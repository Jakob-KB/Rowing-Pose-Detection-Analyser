# src/pose/detect_landmarks.py
import cv2
import mediapipe as mp
import yaml
import os
from pathlib import Path
from src.config import LANDMARK_MAP_R, logger
from src import RowerAnalysis

def detect_landmarks(analysis: RowerAnalysis, overwrite: bool = False) -> None:
    """
    Process raw video from report and save pose data per frame in YAML
    """
    raw_video_path: Path = analysis.raw_video_path
    output_data_path: Path = analysis.landmark_data_path

    # Check that the raw video path exists
    if raw_video_path.exists() is False:
        raise FileNotFoundError(f"No raw video file for the analysis was found at {raw_video_path} to "
                                f"detect landmarks for.")

    # Check if landmark data already exists
    if output_data_path.exists():
        if overwrite is False:
            raise FileExistsError("Landmark data for the given analysis already exists. Overwrite or delete the"
                                  "landmark data instead.")
        elif overwrite is True:
            os.remove(output_data_path)
            logger.info("Found existing landmark data file, overwriting it.")

    mp_pose = mp.solutions.pose
    cap = cv2.VideoCapture(str(raw_video_path))
    if not cap.isOpened():
        logger.error(f"Cannot open video {raw_video_path}")
        return

    landmarks_data = []
    frame_num = 0

    # Get mediapipe settings and landmark mapping from report config
    mediapipe_cfg = analysis.config.get("mediapipe", {})
    landmarks_cfg = analysis.config.get("landmarks", LANDMARK_MAP_R)

    with mp_pose.Pose(
        min_detection_confidence=mediapipe_cfg.get("min_detection_confidence", 0.5),
        min_tracking_confidence=mediapipe_cfg.get("min_tracking_confidence", 0.5),
        model_complexity=mediapipe_cfg.get("model_complexity", 2),
        smooth_landmarks=mediapipe_cfg.get("smooth_landmarks", True)
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
                for name, idx in landmarks_cfg.items():
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
        with open(output_data_path, "w") as f:
            yaml.safe_dump(landmarks_data, f, default_flow_style=False)
        logger.info(f"Saved pose data to {output_data_path}")
    except Exception as e:
        logger.error(f"Error saving pose data: {e}")
        raise

if __name__ == "__main__":
    # For testing load existing report or create a new one
    from src.config import DATA_DIR

    title = "athlete_1"
    input_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
    sample_analysis = RowerAnalysis(title, input_video_path, overwrite=True)
    detect_landmarks(sample_analysis)
