# src/pose/detect_landmarks.py
import cv2
import mediapipe as mp
import json
from pathlib import Path

from src.config import DATA_DIR, REPORTS_DIR, logger, RIGHT_FACING_LANDMARKS
from src.utils import validate_directory, validate_file


class PoseVideoProcessor:
    """
    A class to process videos using MediaPipe Pose, annotate frames with only left-side landmarks
    (and a skeleton connecting them), and export those pose landmarks to a JSON file.
    """
    def __init__(self, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 display: bool = True,
                 facing_direction: str = "right"):
        """
        Initialize the video processor with the desired parameters.
        """
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.display = display
        self.facing_direction = facing_direction

        # Initialize MediaPipe pose module.
        self.mp_pose = mp.solutions.pose

        # Landmarks to draw on the output video (left side only)
        self.landmarks = RIGHT_FACING_LANDMARKS

        # Compute the set of landmark indices.
        self.landmark_indices = set(self.landmarks.values())

        # From the default Pose connections, filter only those connections where both endpoints
        # are in the landmark_indices.
        self.connections = [
            (start, end) for (start, end) in self.mp_pose.POSE_CONNECTIONS
            if start in self.landmark_indices and end in self.landmark_indices
        ]

    def process_video(self, input_path: Path, output_path: Path) -> None:
        """
        Process an input video with MediaPipe Pose estimation, annotate frames with only selected landmarks
        (drawing a skeleton connecting them and a line between ear and shoulder), and save those landmarks to
        a JSON file.
        """
        # Validate the input file and output directory.
        if not validate_file(input_path, create_if_missing=False):
            raise ValueError(f"Invalid input file: {input_path}")
        if not validate_directory(output_path, create_if_missing=True):
            raise ValueError(f"Invalid output directory: {output_path}")

        # Define output file paths
        video_output_path = output_path / f"{input_path.stem}_labeled_video.mp4"
        pose_data_output_path = output_path / f"{input_path.stem}_pose_data.json"

        # Open the video file
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Error opening video file: {input_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30  # Default to 30 FPS if unavailable

        # Prepare video writer using the output video path
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_output_path), fourcc, fps, (width, height))

        frame_number = 0
        pose_data = []

        # Initialize MediaPipe Pose in a context manager to ensure proper cleanup
        with self.mp_pose.Pose(min_detection_confidence=self.min_detection_confidence,
                               min_tracking_confidence=self.min_tracking_confidence) as pose:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number += 1
                # Convert the BGR image to RGB and process with MediaPipe Pose
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = pose.process(image)

                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # If pose landmarks are detected, annotate the frame and collect left-side data
                if results.pose_landmarks:
                    frame_landmarks = {}

                    # Draw circles for each left-side landmark without text
                    for landmark_name, landmark_index in self.landmarks.items():
                        landmark = results.pose_landmarks.landmark[landmark_index]
                        px = int(landmark.x * width)
                        py = int(landmark.y * height)
                        cv2.circle(image, (px, py), 5, (0, 255, 0), -1)
                        frame_landmarks[landmark_name] = {
                            "landmark_index": landmark_index,
                            "x": landmark.x,
                            "y": landmark.y,
                            "visibility": landmark.visibility
                        }

                    # Draw skeleton using only left-side connections
                    for connection in self.connections:
                        start_idx, end_idx = connection
                        start_lm = results.pose_landmarks.landmark[start_idx]
                        end_lm = results.pose_landmarks.landmark[end_idx]
                        start_point = (int(start_lm.x * width), int(start_lm.y * height))
                        end_point = (int(end_lm.x * width), int(end_lm.y * height))
                        cv2.line(image, start_point, end_point, (0, 255, 0), 2)

                    # Draw additional line between EarR and ShoulderR
                    ear_idx = self.landmarks.get("EarR")
                    shoulder_idx = self.landmarks.get("ShoulderR")
                    if ear_idx is not None and shoulder_idx is not None:
                        ear_lm = results.pose_landmarks.landmark[ear_idx]
                        shoulder_lm = results.pose_landmarks.landmark[shoulder_idx]
                        ear_point = (int(ear_lm.x * width), int(ear_lm.y * height))
                        shoulder_point = (int(shoulder_lm.x * width), int(shoulder_lm.y * height))
                        cv2.line(image, ear_point, shoulder_point, (0, 255, 0), 2)

                    # Append the collected landmarks for this frame to the pose data list
                    pose_data.append({"frame": frame_number, "landmarks": frame_landmarks})

                # Write the annotated frame to the output video file
                out.write(image)

                # Optionally display the frame in a window.
                if self.display:
                    cv2.imshow('MediaPipe Pose', image)
                    if cv2.waitKey(10) & 0xFF == ord('q'):
                        break

        # Save the JSON file with the collected pose data
        with open(pose_data_output_path, 'w') as json_file:
            json.dump(pose_data, json_file, indent=4)

        # Release resources
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        logger.info(f"Processing complete. Outputs saved to {output_path}")


if __name__ == "__main__":
    # Example usage:
    title = "athlete_1"
    sample_input_path = DATA_DIR / "videos" / f"{title}.mp4"
    sample_output_path = REPORTS_DIR / f"{sample_input_path.stem}_report"

    processor = PoseVideoProcessor(display=False)
    processor.process_video(sample_input_path, sample_output_path)
