# src/video_processing/process_landmarks.py
import cv2
import mediapipe as mp

from src.config import logger, cfg
from src.session import Session
from src.landmark_dataclasses import LandmarkData


class ProcessLandmarks:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self) -> LandmarkData:
        """
        Read the raw video_metadata, run Mediapipe pose detection,
        and return a LandmarkData object containing all frames & landmarks.
        This method does NOT write to any file directly.
        """
        # Initialize Mediapipe Pose
        mp_pose = mp.solutions.pose.Pose(
            min_detection_confidence=cfg.mediapipe_prefs.min_detection_confidence,
            min_tracking_confidence=cfg.mediapipe_prefs.min_tracking_confidence,
            model_complexity=cfg.mediapipe_prefs.model_complexity,
            smooth_landmarks=cfg.mediapipe_prefs.smooth_landmarks
        )

        # Open the raw video_metadata
        cap = cv2.VideoCapture(str(self.session.raw_video_path))
        if not cap.isOpened():
            msg = f"Cannot open video_metadata {self.session.raw_video_path}"
            logger.error(msg)
            raise RuntimeError(msg)

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


# Example usage
if __name__ == "__main__":
    from src.config import SESSIONS_DIR
    from src.session import Session

    title = "athlete_1"
    session_folder = SESSIONS_DIR / title
    sample_session = Session.load_existing_session(session_folder)

    pose_estimator = ProcessLandmarks(sample_session)
    data = pose_estimator.run()

    print("Got LandmarkData:", data)
