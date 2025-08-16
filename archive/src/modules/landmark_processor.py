# src/modules/landmark_processor.py

from pathlib import Path
import yaml
import cv2
import mediapipe as mp

from src.config import logger, cfg
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.video_metadata import VideoMetadata
from src.utils.status_callback import status_callback
from src.utils.exceptions import ProcessCancelled


class LandmarkProcessor:
    cancellation_message = "Cancelled."
    success_message = "Success."

    def __init__(self, mediapipe_preferences: MediapipePreferences = MediapipePreferences()) -> None:
        self.mediapipe_preferences = mediapipe_preferences
        self._is_cancelled = False

    def run(
        self,
        raw_video_path: Path,
        video_metadata: VideoMetadata,
        file_path: Path,
        status=status_callback
    ) -> LandmarkData:
        self._is_cancelled = False

        cap = None

        try:
            self._update_status(status,"Starting landmark processing.")

            # Open the video file
            cap = cv2.VideoCapture(str(raw_video_path))
            if not cap.isOpened():
                logger.error(f"Cannot open video {raw_video_path}")
                raise FileNotFoundError(f"Cannot open video {raw_video_path}")

            all_landmarks_dict = {}
            frame_num = 0
            landmark_mapping = cfg.landmarks.mapping

            # Set up Mediapipe Pose.
            mp_pose = mp.solutions.pose.Pose(
                model_complexity=self.mediapipe_preferences.model_complexity,
                smooth_landmarks=self.mediapipe_preferences.smooth_landmarks,
                min_detection_confidence=self.mediapipe_preferences.min_detection_confidence,
                min_tracking_confidence=self.mediapipe_preferences.min_tracking_confidence
            )

            with mp_pose as pose:
                while True:
                    if self._is_cancelled:
                        raise ProcessCancelled(self.cancellation_message)

                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_num += 1

                    # Convert frame from BGR to RGB.
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = pose.process(rgb_frame)

                    if results.pose_landmarks:
                        frame_landmarks = {}
                        for name, idx in landmark_mapping.items():
                            lm = results.pose_landmarks.landmark[idx]
                            frame_landmarks[name] = {
                                "x": int(round(lm.x * video_metadata.width)),
                                "y": int(round(lm.y * video_metadata.height))
                            }
                        all_landmarks_dict[frame_num] = frame_landmarks

                    # Report progress.
                    progress_value = (
                        frame_num / video_metadata.total_frames * 100
                        if hasattr(video_metadata, "total_frames") and video_metadata.total_frames > 0
                        else 0
                    )
                    self._update_status(status, f"Processing Landmarks", progress_value)

            cap.release()
            landmark_data = LandmarkData.from_dict(all_landmarks_dict)

            self._update_status(status, "Saving landmark data to file...")
            self.save_landmark_data_to_file(file_path, landmark_data)

            if self._is_cancelled:
                raise ProcessCancelled(self.cancellation_message)

            self._update_status(status, self.success_message)
            return landmark_data

        except ProcessCancelled as e:
            self._handle_unexpected_exit(file_path, cap)
            raise ProcessCancelled(e)
        except Exception as e:
            self._handle_unexpected_exit(file_path, cap)
            raise Exception(e)

    def cancel(self) -> None:
        self._is_cancelled = True

    @staticmethod
    def load_landmark_data_from_file(file_path: Path) -> LandmarkData:
        if not file_path.exists():
            raise FileNotFoundError(f"Landmark file not found at {file_path}")

        with open(file_path, "r") as f:
            data_dict = yaml.safe_load(f)

        landmark_data = LandmarkData.from_dict(data_dict)
        return landmark_data

    @staticmethod
    def save_landmark_data_to_file(file_path: Path, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()
        with open(file_path, "w") as f:
            yaml.safe_dump(data_dict, f, default_flow_style=False)

    @staticmethod
    def _update_status(status_callback_function, message: str, progress_value: float = None) -> None:
        if status_callback_function:
            status_callback_function(message=message, progress_value=progress_value)

    @staticmethod
    def _handle_unexpected_exit(file_path: Path, cap: cv2.VideoCapture = None) -> None:
        if cap is not None:
            cap.release()
        if file_path.exists():
            file_path.unlink()
