# src/video_processing/pose_estimation.py
import cv2
import mediapipe as mp
import yaml
from pathlib import Path

from src.config import LANDMARK_MAP_R, logger, cfg
from src.utils.file_handler import check_path_is_clear, check_path_exists
from src import Session


class PoseEstimator:
    def __init__(self, session: Session, overwrite: bool = False) -> None:
        # Set current session
        self.session = session

        # Check files and paths from session are valid
        valid, msg = self.validate_paths_and_files()
        if not valid:
            logger.error(msg)
            raise

    def process_landmarks(self):
        """
        Process raw video from report and save video_processing data per frame in YAML
        """
        # Setup mediapipe pose estimation
        mp_pose = mp.solutions.pose
        cap = cv2.VideoCapture(str(self.session.raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video {self.session.raw_video_path}")
            return

        landmarks_data = []
        frame_num = 0

        # Get mediapipe settings and landmark mapping from cfg
        with mp_pose.Pose(
                min_detection_confidence=cfg.mediapipe.min_detection_confidence,
                min_tracking_confidence=cfg.mediapipe.min_tracking_confidence,
                model_complexity=cfg.mediapipe.model_complexity,
                smooth_landmarks=cfg.mediapipe.smooth_landmarks
        ) as pose:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_num += 1
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)
                if results.pose_landmarks:
                    frame_landmarks = {}
                    for name, idx in cfg.landmarks.mapping.items():
                        lm = results.pose_landmarks.landmark[idx]
                        frame_landmarks[name] = {
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                            "visibility": lm.visibility
                        }
                    landmarks_data.append({"frame": frame_num, "landmarks": frame_landmarks})
        cap.release()

        try:
            with open(self.session.landmark_data_path, "w") as f:
                yaml.safe_dump(landmarks_data, f, default_flow_style=False)
            logger.info(f"Landmark Data saved to {self.session.landmark_data_path}")
        except Exception as e:
            logger.error(f"Error saving Landmark Data: {e}")
            raise

    def validate_paths_and_files(self) -> (bool, str):
        valid, msg = check_path_exists(self.session.raw_video_path, "Raw Video")
        if not valid:
            return False, msg

        valid, msg = check_path_is_clear(self.session.landmark_data_path, "Landmark Data",
                                         overwrite=self.session.overwrite)
        if not valid:
            return False, msg

        return True, ""



if __name__ == "__main__":
    from src.session import Session
    from src.config import SESSIONS_DIR

    title = "athlete_1"
    session_folder = SESSIONS_DIR / title
    sample_session = Session.load_existing_session(session_folder)
    pose_estimator = PoseEstimator(sample_session)
    pose_estimator.process_landmarks()
