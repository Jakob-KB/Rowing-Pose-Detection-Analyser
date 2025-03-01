# src/modules/process_landmarks.py
import cv2
import mediapipe as mp
from pathlib import Path

from src.config import logger, cfg
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences


class ProcessLandmarks:
    @staticmethod
    def run(raw_video_path: Path, mediapipe_preferences: MediapipePreferences) -> LandmarkData:
        """
        Read the raw video_metadata, run Mediapipe pose detection,
        and return a LandmarkData object containing all frames & landmarks.
        This method does NOT write to any file directly.
        """

        # Initialize Mediapipe Pose
        mp_pose = mp.solutions.pose.Pose(
            model_complexity=mediapipe_preferences.model_complexity,
            smooth_landmarks=mediapipe_preferences.smooth_landmarks,
            min_detection_confidence=mediapipe_preferences.min_detection_confidence,
            min_tracking_confidence=mediapipe_preferences.min_tracking_confidence
        )

        # Open the raw video_metadata
        cap = cv2.VideoCapture(str(raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video_metadata {raw_video_path}")
            raise

        # Detect landmarks per frame
        all_landmarks_dict = {}
        frame_num = 0
        landmark_mapping = cfg.landmarks.mapping

        with mp_pose as pose:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_num += 1

                # Convert frame from BGR to RGB for Mediapipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)

                if results.pose_landmarks:
                    # Extract each named landmark
                    frame_landmarks = {}
                    for name, idx in landmark_mapping.items():
                        lm = results.pose_landmarks.landmark[idx]
                        frame_landmarks[name] = {
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                            "visibility": lm.visibility
                        }

                    all_landmarks_dict[frame_num] = frame_landmarks

        cap.release()

        # Convert dict to a LandmarkData object
        landmark_data = LandmarkData.from_dict(all_landmarks_dict)
        return landmark_data
