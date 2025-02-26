# src/video_processing/annotate_video.py
import cv2
import numpy as np
import yaml
from typing import Dict, Tuple, Any, List

from src import Session
from src.config import logger, cfg
from src.utils.file_handler import check_path_exists, check_path_is_clear


class AnnotateVideo:
    def __init__(self, _session: Session, overwrite: bool = False) -> None:
        # Store the session object
        self.current_session = _session
        self.overwrite = overwrite

        # Check that all associated paths and files of the current session are valid
        valid, msg = self.validate_paths_and_files()
        if not valid:
            logger.error(msg)
            raise

        # Dotted line variables
        self.dotted_line_landmarks: List[str] = ["ankle", "hip"]
        self.dotted_line_extension: int = 96
        self.dotted_line_colour: Tuple[int, int, int] = (255, 255, 255)
        self.dotted_line_thickness: int = 3
        self.dotted_line_factor: int = 8

    @staticmethod
    def _draw_line(image: np.ndarray,
                   pose_landmarks: Any,
                   idx1: int,
                   idx2: int,
                   width: int,
                   height: int,
                   line_colour: Tuple[int, int, int],
                   line_thickness: int
                   ) -> None:
        """Draw a line between two landmarks."""
        start_lm = pose_landmarks.landmark[idx1]
        end_lm = pose_landmarks.landmark[idx2]
        start_point: Tuple[int, int] = (int(start_lm.x * width), int(start_lm.y * height))
        end_point: Tuple[int, int] = (int(end_lm.x * width), int(end_lm.y * height))
        cv2.line(image, start_point, end_point, line_colour, line_thickness)

    @staticmethod
    def _draw_dotted_line_vertical(image: np.ndarray,
                                   start_point: Tuple[int, int],
                                   extension: int,
                                   color: Tuple[int, int, int],
                                   thickness: int
                                   ) -> None:
        """
        Draw a vertical dotted line starting at start_point,
        extending upward by 'extension' pixels.
        """
        dot_length: int = 8
        gap: int = 8

        x, y = start_point
        end_y = y - extension  # end_y is smaller than y for upward extension
        current_y = y

        while current_y > end_y:
            # Calculate the end of the current dot segment
            segment_end = max(current_y - dot_length, end_y)
            cv2.line(image, (x, current_y), (x, segment_end), color, thickness)
            current_y -= (dot_length + gap)

    def draw_landmarks(self, image: np.ndarray,
                       pose_landmarks: Any,
                       width: int,
                       height: int
                       ) -> Dict[str, Dict[str, float]]:
        """
        Draw landmarks and skeleton connections on the image.
        Returns a dict of drawn landmarks.
        """
        frame_landmarks: Dict[str, Dict[str, float]] = {}

        # Create an overlay copy to draw the landmarks and lines.
        overlay = image.copy()

        # Draw each skeleton connection (line) on the overlay.
        for start_idx, end_idx in cfg.landmarks.connections:
            self._draw_line(
                overlay,
                pose_landmarks,
                start_idx,
                end_idx,
                width,
                height,
                cfg.annotation.skeleton_bone_colour,
                cfg.annotation.skeleton_bone_thickness
            )

        # Draw each landmark as a circle on the overlay.
        for name, idx in cfg.landmarks.mapping.items():
            lm = pose_landmarks.landmark[idx]
            px: int = int(lm.x * width)
            py: int = int(lm.y * height)
            cv2.circle(
                overlay,
                (px, py),
                cfg.annotation.landmark_point_radius,
                cfg.annotation.landmark_point_colour,
                -1
            )
            frame_landmarks[name] = {
                "landmark_index": float(idx),
                "x": lm.x,
                "y": lm.y,
                "visibility": lm.visibility
            }

            # If this landmark should have a dotted line extension, draw it.
            if name in self.dotted_line_landmarks:
                extension = self.dotted_line_extension
                self._draw_dotted_line_vertical(
                        overlay,(px, py), extension, self.dotted_line_colour, self.dotted_line_thickness
                    )

        # Opacity blending
        alpha = cfg.annotation.opacity
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

        return frame_landmarks

    def annotate_video(self) -> None:
        """
        Annotate each frame of the raw video using landmark data from the YAML file.
        The annotated video is saved to the annotated_video_path specified in the session.
        """
        # Load landmark data from YAML
        with open(self.current_session.landmark_data_path, "r") as f:
            landmark_frames = yaml.safe_load(f)
        # Map frame numbers to landmark data
        landmarks_by_frame: Dict[int, Dict[str, Dict[str, float]]] = {
            entry["frame"]: entry["landmarks"] for entry in landmark_frames
        }

        cap = cv2.VideoCapture(str(self.current_session.raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open raw video: {self.current_session.raw_video_path}")
            raise ValueError(f"Cannot open raw video: {self.current_session.raw_video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(self.current_session.annotated_video_path), fourcc, fps, (width, height))

        frame_num = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            # If landmark data exists for this frame, annotate it
            if frame_num in landmarks_by_frame:
                frame_landmarks_data = landmarks_by_frame[frame_num]
                simple_landmarks = SimpleLandmarks(frame_landmarks_data, cfg.landmarks.mapping)
                self.draw_landmarks(frame, simple_landmarks, width, height)
            out.write(frame)

        cap.release()
        out.release()
        logger.info(f"Annotated video saved to {self.current_session.annotated_video_path}")

    def validate_paths_and_files(self) -> (bool, str):
        # Check landmark map and connections are provided in the cfg
        if cfg.landmarks.mapping is None or cfg.landmarks.connections is None:
            msg = "Landmark map and/or landmark connections are missing in the session config."
            return False, msg

        # Check the raw video exists
        valid, msg = check_path_exists(self.current_session.raw_video_path, "Raw Video")
        if not valid:
            return False, msg

        # Check the landmark data exists
        valid, msg = check_path_exists(self.current_session.landmark_data_path, "Landmark Data")
        if not valid:
            return valid, msg

        # Check that the annotated video path is empty
        valid, msg = check_path_is_clear(self.current_session.annotated_video_path, "Annotated Video",
                                          overwrite=self.overwrite)
        if not valid:
            return valid, msg

        return True, ""


class SimpleLandmarks:
    """
    Simple wrapper to mimic a MediaPipe Pose landmarks object using a dictionary.
    Expects a dictionary mapping landmark names to their values and a landmark map.
    """

    def __init__(self, landmarks: Dict[str, Dict[str, float]], landmarks_map: Dict[str, int]) -> None:
        max_idx = max(landmarks_map.values())
        self.landmark = [None] * (max_idx + 1)
        for name, idx in landmarks_map.items():
            data = landmarks.get(name)
            if data is not None:
                # Create a simple object with attributes x, y, and visibility
                self.landmark[idx] = type("Landmark", (), data)
            else:
                self.landmark[idx] = type("Landmark", (), {"x": 0.0, "y": 0.0, "visibility": 0.0})


# Example usage:
if __name__ == "__main__":
    from src.session import Session
    from src.config import SESSIONS_DIR

    title = "athlete_1"
    session_folder = SESSIONS_DIR / title
    sample_session = Session.load_existing_session(session_folder)
    annotator = AnnotateVideo(sample_session, overwrite=True)
    annotator.annotate_video()
