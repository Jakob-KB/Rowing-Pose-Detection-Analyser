# src/pose/annotate_video.py
import cv2
import numpy as np
from typing import Dict, Tuple, List, Any
from pathlib import Path

from matplotlib.pyplot import connect

from src import RowerAnalysis
from src.config import logger

def annotate_video(analysis: RowerAnalysis, overwrite: bool = False) -> None:

    # Load landmark map and connections from analysis config
    landmark_map: Dict[str, int] = analysis.config["landmark_map"]
    landmark_connections: List[Tuple[(int, int)]] = analysis.config["landmark_connections"]

    # Load raw video path, landmark data path and the annotated video path to output at
    raw_video_path: Path = analysis.raw_video_path
    annotated_video_path: Path = analysis.annotated_video_path
    landmark_data_path: Path = analysis.landmark_data_path

    # Check landmark map and connections are set
    if landmark_map is None or landmark_connections is None:
        raise ValueError("Landmark map and/or landmark connections are None. Check analysis config.")

    # Check raw video path and landmark data exist
    if raw_video_path.exists() is False:
        raise FileNotFoundError(f"No raw video file for the analysis was found at {raw_video_path} to annotate.")
    if landmark_data_path.exists() is False:
        raise FileNotFoundError(f"No landmark data was found at {landmark_data_path}, required to annotate video.")

    # Check if an annotated video already exists
    if annotated_video_path.exists():
        if overwrite is False:
            raise FileExistsError("An annotated video already exists for this analysis, either overwrite or "
                                  "delete it instead.")
        if overwrite is True:
            logger.info("An annotated video already exists for this analysis, overwriting it")

class LandmarkDrawer:
    def __init__(self, landmarks_map: Dict[str, int], connections: List[Tuple[int, int]]) -> None:
        """
        :param landmarks_map: A dict mapping landmark names to indices.
        :param connections: A list of tuples (start_idx, end_idx) for skeleton connections.
        """
        self.landmarks_map: Dict[str, int] = landmarks_map
        self.connections: List[Tuple[int, int]] = connections

    @staticmethod
    def _draw_line(image: np.ndarray, pose_landmarks: Any, idx1: int, idx2: int, width: int, height: int) -> None:
        """
        Helper method to draw a line between two landmarks.
        """
        start_lm = pose_landmarks.landmark[idx1]
        end_lm = pose_landmarks.landmark[idx2]
        start_point: Tuple[int, int] = (int(start_lm.x * width), int(start_lm.y * height))
        end_point: Tuple[int, int] = (int(end_lm.x * width), int(end_lm.y * height))
        cv2.line(image, start_point, end_point, (0, 255, 0), 2)

    def draw_landmarks(self, image: np.ndarray,
                       pose_landmarks: Any,
                       width: int,
                       height: int) -> Dict[str, Dict[str, float]]:
        """
        Draw landmarks and skeleton connections on the image.

        :param image: The image/frame on which to draw.
        :param pose_landmarks: The landmarks from MediaPipe Pose.
        :param width: Image width for coordinate scaling.
        :param height: Image height for coordinate scaling.
        :return: A dict of drawn landmarks with their normalized values.
        """
        frame_landmarks: Dict[str, Dict[str, float]] = {}

        # Draw each landmark as a circle.
        for name, idx in self.landmarks_map.items():
            lm = pose_landmarks.landmark[idx]
            px: int = int(lm.x * width)
            py: int = int(lm.y * height)
            cv2.circle(image, (px, py), 5, (0, 255, 0), -1)
            frame_landmarks[name] = {
                "landmark_index": float(idx),
                "x": lm.x,
                "y": lm.y,
                "visibility": lm.visibility
            }

        # Combine default skeleton connections with an extra connection if available.
        all_connections: List[Tuple[int, int]] = self.connections.copy()
        ear_idx = self.landmarks_map.get("EarR")
        shoulder_idx = self.landmarks_map.get("ShoulderR")
        if ear_idx is not None and shoulder_idx is not None:
            all_connections.append((ear_idx, shoulder_idx))

        # Draw all connections using the helper method.
        for start_idx, end_idx in all_connections:
            self._draw_line(image, pose_landmarks, start_idx, end_idx, width, height)

        return frame_landmarks
