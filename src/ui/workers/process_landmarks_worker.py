import re
import subprocess
import shutil
import yaml
from pathlib import Path
import mediapipe as mp
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import imageio_ffmpeg as ffmpeg

from src.config import cfg, logger
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.video_metadata import VideoMetadata
from src.utils.video_handler import get_total_frames
from src.models.landmark_data import LandmarkData

class ProcessLandmarksWorker(QThread):
    progress = pyqtSignal(str, int)    # (status message, progress percentage)
    resultReady = pyqtSignal(object)   # Emits the LandmarkData result (as an object)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        raw_video_path: Path,
        landmark_data_path: Path,
        video_metadata: VideoMetadata,
        mediapipe_preferences: MediapipePreferences = MediapipePreferences(),
        parent=None
    ) -> None:
        super().__init__(parent)
        self.raw_video_path: Path = raw_video_path
        self.landmark_data_path: Path = landmark_data_path
        self.video_metadata: VideoMetadata = video_metadata
        self.mediapipe_preferences: MediapipePreferences = mediapipe_preferences

        self.landmark_data: LandmarkData | None = None

        self._is_canceled: bool = False

    def cancel(self):
        """Signal the thread to cancel its work."""
        self._is_canceled = True

    def _cleanup(self):
        """Remove the landmark data file if it exists."""
        if self.landmark_data_path.exists():
            self.landmark_data_path.unlink()
            logger.info(f"Landmark data file {self.landmark_data_path} deleted due to cancellation.")

    def run(self):
        try:
            # Initialize Mediapipe pose solution.
            mp_pose = mp.solutions.pose.Pose(
                model_complexity=self.mediapipe_preferences.model_complexity,
                smooth_landmarks=self.mediapipe_preferences.smooth_landmarks,
                min_detection_confidence=self.mediapipe_preferences.min_detection_confidence,
                min_tracking_confidence=self.mediapipe_preferences.min_tracking_confidence
            )

            # Open the video.
            cap = cv2.VideoCapture(str(self.raw_video_path))
            if not cap.isOpened():
                error_msg = f"Cannot open video {self.raw_video_path}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            all_landmarks_dict = {}
            frame_num = 0
            landmark_mapping = cfg.landmarks.mapping

            with mp_pose as pose:
                while True:
                    # Check for cancellation.
                    if self._is_canceled:
                        cap.release()
                        self._cleanup()
                        self.canceled.emit()
                        return

                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_num += 1

                    # Convert frame from BGR to RGB for Mediapipe.
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = pose.process(rgb_frame)

                    if results.pose_landmarks:
                        # Extract each named landmark.
                        frame_landmarks = {}
                        for name, idx in landmark_mapping.items():
                            lm = results.pose_landmarks.landmark[idx]
                            frame_landmarks[name] = {
                                "x": int(round(lm.x * self.video_metadata.width)),
                                "y": int(round(lm.y * self.video_metadata.height))
                            }
                        all_landmarks_dict[frame_num] = frame_landmarks

                    # Emit progress every 10 frames.
                    if frame_num % 10 == 0:
                        total_frames = get_total_frames(self.raw_video_path)
                        progress_percent = int((frame_num / total_frames) * 100) if total_frames > 0 else 0
                        self.progress.emit("Processing frame", progress_percent)

            cap.release()

            # Check for cancellation after the loop.
            if self._is_canceled:
                self._cleanup()
                self.canceled.emit()
                return

            # Create a LandmarkData object from the collected dictionary.
            self.landmark_data = LandmarkData.from_dict(all_landmarks_dict)
            logger.info("Processed landmark data.")

            # Write the landmark data to file.
            data_dict = self.landmark_data.to_dict()
            with open(self.landmark_data_path, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {self.landmark_data_path}")

            # Emit the result using the dedicated signal.
            self.resultReady.emit(self.landmark_data)
            self.finished.emit()

        except Exception as e:
            error_msg = f"Error processing video: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
