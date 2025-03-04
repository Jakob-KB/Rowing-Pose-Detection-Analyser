# src/modules/process_landmarks.py

from pathlib import Path

import cv2
import mediapipe as mp

from src.config import logger, cfg
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.video_metadata import VideoMetadata


class ProcessLandmarks:
    @staticmethod
    def run(
            raw_video_path: Path,
            video_metadata: VideoMetadata,
            mediapipe_preferences: MediapipePreferences,
            progress_callback = None
    ) -> LandmarkData:

        mp_pose = mp.solutions.pose.Pose(
            model_complexity=mediapipe_preferences.model_complexity,
            smooth_landmarks=mediapipe_preferences.smooth_landmarks,
            min_detection_confidence=mediapipe_preferences.min_detection_confidence,
            min_tracking_confidence=mediapipe_preferences.min_tracking_confidence
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

                # Update progress
                if progress_callback:
                    progress = (frame_num / video_metadata.total_frames) * 100
                    if frame_num % 10 == 0 or frame_num == video_metadata.total_frames:
                        progress_callback("Processing pose", progress)

        cap.release()

        # Convert dict to a LandmarkData object
        landmark_data = LandmarkData.from_dict(all_landmarks_dict)
        return landmark_data
