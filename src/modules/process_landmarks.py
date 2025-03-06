# src/modules/process_landmarks.py

from pathlib import Path
import yaml

import cv2
import mediapipe as mp

from src.config import logger, cfg
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.video_metadata import VideoMetadata


class ProcessLandmarks:
    def __init__(self, mediapipe_preferences: MediapipePreferences) -> None:
        self.mediapipe_preferences: MediapipePreferences = mediapipe_preferences

    def run(self,
            raw_video_path: Path,
            video_metadata: VideoMetadata
    ) -> LandmarkData:

        mp_pose = mp.solutions.pose.Pose(
            model_complexity=self.mediapipe_preferences.model_complexity,
            smooth_landmarks=self.mediapipe_preferences.smooth_landmarks,
            min_detection_confidence=self.mediapipe_preferences.min_detection_confidence,
            min_tracking_confidence=self.mediapipe_preferences.min_tracking_confidence
        )

        cap = cv2.VideoCapture(str(raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video {raw_video_path}")
            raise

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
                            "x": int(round(lm.x * video_metadata.width)),
                            "y": int(round(lm.y * video_metadata.height))
                        }

                    all_landmarks_dict[frame_num] = frame_landmarks

        cap.release()

        # Convert dict to a LandmarkData object
        landmark_data = LandmarkData.from_dict(all_landmarks_dict)

        logger.info(f"Processed landmark data.")
        return landmark_data

    @staticmethod
    def load_landmark_data_from_file(file_path: Path) -> LandmarkData:
        if not file_path.exists():
            raise FileNotFoundError(f"Landmark file not found at {file_path}")

        with open(file_path, "r") as f:
            data_dict = yaml.safe_load(f)

        landmark_data = LandmarkData.from_dict(data_dict)
        logger.info(f"Landmark data loaded from {file_path}")
        return landmark_data

    @staticmethod
    def save_landmark_data_to_file(file_path: Path, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()

        try:
            with open(file_path, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {file_path}")
        except Exception as e:
            raise FileNotFoundError(f"Error saving landmark data: {e}")

    def update_mediapipe_preferences(self, mediapipe_preferences: MediapipePreferences) -> None:
        self.mediapipe_preferences = mediapipe_preferences
