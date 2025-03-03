# src/modules/process_landmarks.py

from pathlib import Path
import cv2
import mediapipe as mp

from src.config import logger, cfg
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.video_metadata import VideoMetadata
from src.utils.exceptions import CancellationException
from src.models.cancelable_process import CancelableProcess

class ProcessLandmarks(CancelableProcess):
    def __init__(
        self,
        raw_video_path: Path,
        video_metadata: VideoMetadata,
        mediapipe_preferences: MediapipePreferences
    ):
        super().__init__()
        self.raw_video_path = raw_video_path
        self.video_metadata = video_metadata
        self.mediapipe_preferences = mediapipe_preferences

    def run(self) -> LandmarkData:
        """
        Process the video and extract pose landmarks.
        Uses the base class's cancellation and progress reporting features.
        """
        mp_pose = mp.solutions.pose.Pose(
            model_complexity=self.mediapipe_preferences.model_complexity,
            smooth_landmarks=self.mediapipe_preferences.smooth_landmarks,
            min_detection_confidence=self.mediapipe_preferences.min_detection_confidence,
            min_tracking_confidence=self.mediapipe_preferences.min_tracking_confidence
        )

        cap = cv2.VideoCapture(str(self.raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video {self.raw_video_path}")
            raise RuntimeError(f"Cannot open video {self.raw_video_path}")

        all_landmarks = {}
        landmark_mapping = cfg.landmarks.mapping
        frame_num = 0

        with mp_pose as pose:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_num += 1

                # Check cancellation state.
                if self.is_cancelled():
                    cap.release()
                    raise CancellationException("Pose processing was cancelled.")

                # Report progress every 10 frames or at the end.
                progress = (frame_num / self.video_metadata.total_frames) * 100
                if frame_num % 10 == 0 or frame_num == self.video_metadata.total_frames:
                    self.report_progress("Processing landmarks", progress)

                # Convert frame to RGB for mediapipe.
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)

                if results.pose_landmarks:
                    frame_landmarks = {}
                    for name, idx in landmark_mapping.items():
                        lm = results.pose_landmarks.landmark[idx]
                        frame_landmarks[name] = {
                            "x": int(round(lm.x * self.video_metadata.width)),
                            "y": int(round(lm.y * self.video_metadata.height))
                        }
                    all_landmarks[frame_num] = frame_landmarks

        cap.release()
        return LandmarkData.from_dict(all_landmarks)
