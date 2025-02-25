# src/pose/detect_pose_landmarks.py
import cv2
import mediapipe as mp
import numpy as np
from typing import Any


class LandmarkDetector:
    def __init__(self, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5) -> None:
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def detect(self, frame: np.ndarray) -> Any:
        """
        Process the frame using MediaPipe Pose and return the detection results.

        :param frame: An image in BGR format.
        :return: The results from MediaPipe Pose.
        """
        # Convert from BGR to RGB.
        rgb_frame: np.ndarray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results: Any = self.pose.process(rgb_frame)
        rgb_frame.flags.writeable = True
        return results
