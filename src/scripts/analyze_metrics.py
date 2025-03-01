# src/scripts/analyze_metrics.py
import cv2
import json
import math
from pathlib import Path
from src.config import SESSIONS_DIR, logger
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt


def compute_angle(point1, point2, ref_vector=(-1, 0)):
    """
    Computes the angle (in degrees) between the vector from point2 to point1 and a reference vector.
    """
    dx = point1["x"] - point2["x"]
    dy = point1["y"] - point2["y"]
    norm = math.sqrt(dx ** 2 + dy ** 2)
    if norm == 0:
        return None
    cos_angle = -dx / norm  # using ref_vector (-1, 0)
    cos_angle = max(min(cos_angle, 1), -1)
    return math.degrees(math.acos(cos_angle))


class RowingStrokeAnalyzer:
    """
    Analyzes a labeled video_metadata along with corresponding JSON video_processing data.
    """

    def __init__(self, video_path: Path, json_path: Path, stroke_threshold: float = 0.01):
        self.video_path = video_path
        self.json_path = json_path
        self.stroke_threshold = stroke_threshold

        self.pose_data = self._load_pose_data()
        self.analysis_results = []  # List of per-frame session data.
        self.transitions = []       # List of (frame_index, transition_type)
        self.stroke_count = 0

        # For robust direction estimation.
        self.prev_x_list = []  # Stores recent HandR x values.
        self.prev_basic_stage = None  # Last determined stage: "drive", "recovery", or "unknown"

        # For slide position.
        self.avg_ankle = None
        self.min_hip = None

    def _load_pose_data(self):
        """Loads and sorts video_processing data from the JSON file."""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            return sorted(data, key=lambda x: x.get("frame", 0))
        except Exception as e:
            logger.error(f"Error loading video_processing data from {self.json_path}: {e}")
            return []

    def analyze_video(self):
        """
        Processes the video_metadata frame-by-frame, computes scripts for each frame,
        and stores the results.
        """
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise ValueError(f"Error opening video_metadata file: {self.video_path}")

        pose_index = 0
        total_pose_entries = len(self.pose_data)
        frame_index = 0

        # For slide position computation.
        ankle_x_vals = []
        hip_x_vals = []

        while cap.isOpened():
            ret, _ = cap.read()
            if not ret:
                break

            current_pose = None
            if pose_index < total_pose_entries:
                if self.pose_data[pose_index].get("frame") == frame_index:
                    current_pose = self.pose_data[pose_index]
                    pose_index += 1

            result = self._process_frame(frame_index, current_pose)
            self.analysis_results.append(result)

            if result.get("current_ankle_x") is not None:
                ankle_x_vals.append(result["current_ankle_x"])
            if result.get("current_hip_x") is not None:
                hip_x_vals.append(result["current_hip_x"])

            frame_index += 1

        cap.release()
        logger.info("Basic session complete.")
        self._compute_slide_position(ankle_x_vals, hip_x_vals)

    def _process_frame(self, frame_index, current_pose):
        """
        Processes an individual frame’s video_processing data and returns computed analysis.
        """
        result = {
            "frame": frame_index,
            "hand_x": None,
            "basic_stage": "unknown",
            "stroke_count": self.stroke_count,
            "knee_angle": None,
            "torso_angle": None,
            "current_ankle_x": None,
            "current_hip_x": None,
            "slide_position": None,
            "stage": "unknown"
        }

        if current_pose:
            landmarks = current_pose.get("landmarks", {})

            # Process hand movement to determine basic stage.
            result.update(self._process_hand_stage(landmarks, frame_index))

            # Compute knee angle and record AnkleR x-position.
            knee_angle, ankle_x = self._compute_knee_angle(landmarks)
            result["knee_angle"] = knee_angle
            result["current_ankle_x"] = ankle_x

            # Compute torso angle and record HipR x-position.
            torso_angle, hip_x = self._compute_torso_angle(landmarks)
            result["torso_angle"] = torso_angle
            result["current_hip_x"] = hip_x

        return result

    def _process_hand_stage(self, landmarks, frame_index):
        """
        Uses the HandR landmark to compute the x-position and determine the basic stage.
        Also updates the stroke count and records transitions.
        """
        data = {"hand_x": None, "basic_stage": "unknown"}
        if "HandR" not in landmarks:
            logger.warning(f"Frame {frame_index} missing HandR landmark.")
            return data

        hand_x = landmarks["HandR"]["x"]
        data["hand_x"] = hand_x
        self.prev_x_list.append(hand_x)
        if len(self.prev_x_list) > 4:
            self.prev_x_list.pop(0)

        if len(self.prev_x_list) >= 4:
            avg_prev = sum(self.prev_x_list[:-1]) / (len(self.prev_x_list) - 1)
            delta = hand_x - avg_prev

            if delta > self.stroke_threshold:
                current_direction = "right"
            elif delta < -self.stroke_threshold:
                current_direction = "left"
            else:
                current_direction = self.prev_basic_stage

            if current_direction == "right":
                data["basic_stage"] = "recovery"
            elif current_direction == "left":
                data["basic_stage"] = "drive"
            else:
                data["basic_stage"] = "unknown"

            prev_stage = self.prev_basic_stage if self.prev_basic_stage is not None else "unknown"
            if prev_stage != "unknown" and data["basic_stage"] != prev_stage:
                if prev_stage == "drive" and data["basic_stage"] == "recovery":
                    self.transitions.append((frame_index, "drive_to_recovery"))
                    self.stroke_count += 1
                    logger.info(f"Frame {frame_index}: drive->recovery transition (stroke: {self.stroke_count})")
                elif prev_stage == "recovery" and data["basic_stage"] == "drive":
                    self.transitions.append((frame_index, "recovery_to_drive"))
                    logger.info(f"Frame {frame_index}: recovery->drive transition")
            if abs(delta) >= self.stroke_threshold:
                self.prev_basic_stage = data["basic_stage"]

        return data

    def _compute_knee_angle(self, landmarks):
        """
        Computes the knee angle (using KneeR and AnkleR) and returns the angle and AnkleR x-position.
        """
        knee_angle = None
        ankle_x = None
        if "KneeR" in landmarks and "AnkleR" in landmarks:
            knee = landmarks["KneeR"]
            ankle = landmarks["AnkleR"]
            vx = knee["x"] - ankle["x"]
            vy = knee["y"] - ankle["y"]
            norm = math.sqrt(vx ** 2 + vy ** 2)
            if norm > 0:
                knee_angle = math.degrees(math.acos(max(min(-vx / norm, 1), -1)))
            ankle_x = ankle["x"]
        return knee_angle, ankle_x

    def _compute_torso_angle(self, landmarks):
        """
        Computes the torso angle (using ShoulderR and HipR) and returns the angle and HipR x-position.
        """
        torso_angle = None
        hip_x = None
        if "ShoulderR" in landmarks and "HipR" in landmarks:
            shoulder = landmarks["ShoulderR"]
            hip = landmarks["HipR"]
            vx = shoulder["x"] - hip["x"]
            vy = shoulder["y"] - hip["y"]
            norm = math.sqrt(vx ** 2 + vy ** 2)
            if norm > 0:
                torso_angle = math.degrees(math.acos(max(min(-vx / norm, 1), -1)))
            hip_x = hip["x"]
        return torso_angle, hip_x

    def _compute_slide_position(self, ankle_x_vals, hip_x_vals):
        """Computes the slide position and updates session results."""
        self.avg_ankle = sum(ankle_x_vals) / len(ankle_x_vals) if ankle_x_vals else None
        self.min_hip = min(hip_x_vals) if hip_x_vals else None

        logger.info(f"Computed avg_ankle: {self.avg_ankle}, min_hip: {self.min_hip}")

        if self.avg_ankle is not None and self.min_hip is not None and (self.avg_ankle - self.min_hip) != 0:
            for result in self.analysis_results:
                current_hip_x = result.get("current_hip_x")
                if current_hip_x is not None:
                    slide = 100 * (self.avg_ankle - current_hip_x) / (self.avg_ankle - self.min_hip)
                    result["slide_position"] = max(0, min(100, slide))
                else:
                    result["slide_position"] = None
        else:
            logger.error("Slide position computation failed due to insufficient data.")

    def mark_transition_stages(self, transition_window: int = 10):
        """
        Adjust frames around transitions:
          - For drive→recovery, mark frames within ±transition_window as "finish".
          - For recovery→drive, mark frames as "catch".
        """
        for event_frame, event_type in self.transitions:
            start = max(0, event_frame - transition_window)
            end = min(len(self.analysis_results) - 1, event_frame + transition_window)
            new_stage = "finish" if event_type == "drive_to_recovery" else "catch"
            for i in range(start, end + 1):
                self.analysis_results[i]["stage"] = new_stage

        for result in self.analysis_results:
            if not result.get("stage") or result["stage"] in ("unknown", None):
                result["stage"] = result.get("basic_stage", "unknown")

    def calculate_hand_speed(self, index, window=2):
        """
        Computes the average hand speed for frame 'index' using a symmetric window,
        and determines the net direction of movement.

        Returns:
          (avg_speed, direction) where direction is "left", "right", or "stationary".
        """
        speeds = []
        directions = []
        total_frames = len(self.analysis_results)
        start = max(1, index - window)
        end = min(total_frames - 1, index + window)
        for j in range(start, end + 1):
            current = self.analysis_results[j].get("hand_x")
            prev = self.analysis_results[j - 1].get("hand_x")
            if current is not None and prev is not None:
                delta = current - prev
                speeds.append(abs(delta))
                if delta > 0:
                    directions.append("right")
                elif delta < 0:
                    directions.append("left")
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        if directions:
            net_direction = max(set(directions), key=directions.count)
        else:
            net_direction = "stationary"
        return avg_speed, net_direction

    def _draw_overlay(self, frame, result):
        """
        Overlays session text on a frame.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        y = 30
        if result["hand_x"] is not None:
            cv2.putText(frame, f"HandR x: {result['hand_x']:.2f}", (10, y),
                        font, 1, (0, 255, 0), 2, cv2.LINE_AA)
            y += 30
        cv2.putText(frame, f"Stage: {result['stage']}", (10, y),
                    font, 1, (0, 255, 0), 2, cv2.LINE_AA)
        y += 30
        cv2.putText(frame, f"Strokes: {result['stroke_count']}", (10, y),
                    font, 1, (0, 255, 0), 2, cv2.LINE_AA)
        y += 30
        if result["knee_angle"] is not None:
            cv2.putText(frame, f"Knee angle: {result['knee_angle']:.1f}°", (10, y),
                        font, 1, (255, 0, 0), 2, cv2.LINE_AA)
            y += 30
        if result["torso_angle"] is not None:
            cv2.putText(frame, f"Torso angle: {result['torso_angle']:.1f}°", (10, y),
                        font, 1, (255, 0, 0), 2, cv2.LINE_AA)
            y += 30
        if result["slide_position"] is not None:
            cv2.putText(frame, f"Slide Position: {result['slide_position']:.0f}%", (10, y),
                        font, 1, (0, 0, 255), 2, cv2.LINE_AA)
        return frame

    def display_analysis(self, speed_window: int = 2, graph_window: int = 50):
        """
        Overlays session data on video_metadata frames and displays them.
        Also opens a matplotlib window to plot hand speed (from calculate_hand_speed)
        in real time. The plot rotates to show only the last 'graph_window' frames.

        Press 'q' to quit.
        """
        if not self.analysis_results:
            logger.error("No session results available. Run analyze_video() first.")
            return

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise ValueError(f"Error opening video_metadata file: {self.video_path}")
        cv2.namedWindow("Rowing Stroke Analysis", cv2.WINDOW_NORMAL)

        plt.ion()
        fig, ax = plt.subplots()
        hand_speed_line, = ax.plot([], [], 'r-', label="Hand Speed")
        ax.set_xlabel("Frame")
        ax.set_ylabel("Hand Speed (avg delta)")
        ax.legend()
        plt.title("Real-Time Hand Speed")

        plot_frames = []
        plot_speeds = []
        total_frames = len(self.analysis_results)

        frame_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_index < total_frames:
                result = self.analysis_results[frame_index]
                frame = self._draw_overlay(frame, result)
                avg_speed, direction = self.calculate_hand_speed(frame_index, window=speed_window)

                # Append the current frame and speed; keep only the last graph_window entries.
                plot_frames.append(frame_index)
                plot_speeds.append(avg_speed)
                if len(plot_frames) > graph_window:
                    plot_frames = plot_frames[-graph_window:]
                    plot_speeds = plot_speeds[-graph_window:]

                hand_speed_line.set_data(plot_frames, plot_speeds)
                ax.relim()
                ax.autoscale_view(True, True, True)
                plt.draw()
                plt.pause(0.001)

            cv2.imshow("Rowing Stroke Analysis", frame)
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
            frame_index += 1

        cap.release()
        cv2.destroyAllWindows()
        plt.ioff()
        plt.show()


# ------------------------------------------------------------------------------
# Main Function
# ------------------------------------------------------------------------------
def main():
    title = "athlete_1"
    base_dir = SESSIONS_DIR / f"{title}_report"
    video_path = base_dir / f"{title}_labeled_video.mp4"
    json_path = base_dir / f"{title}_pose_data.json"
    analyzed_video_path = base_dir / f"{title}_analyzed_video.mp4"

    analyzer = RowingStrokeAnalyzer(video_path, json_path, stroke_threshold=0.001)
    analyzer.analyze_video()
    analyzer.mark_transition_stages(transition_window=6)
    # analyzer.save_analysis_video(analyzed_video_path)
    analyzer.display_analysis(speed_window=4, graph_window=200)


if __name__ == "__main__":
    main()
