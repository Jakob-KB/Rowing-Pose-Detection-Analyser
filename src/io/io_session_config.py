from datetime import datetime
import json
from src.config import SESSIONS_DIR, cfg, logger
from typing import Dict


def apply_config(session, config: Dict) -> None:
    session.title = config.get("session_title")
    if not session.title:
        raise ValueError("No 'session_title' in config")

    session.overwrite = config.get("overwrite", False)

    session_dir = SESSIONS_DIR / session.title

    # Rebuild the paths
    session.session_dir = session_dir
    session.raw_video_path = session_dir / cfg.session_file_names.raw_video
    session.annotated_video_path = session_dir / cfg.session_file_names.annotated_video
    session.landmark_data_path = session_dir / cfg.session_file_names.landmark_data
    session.analysis_data_path = session_dir / cfg.session_file_names.analysis_data
    session.session_config_path = session_dir / cfg.session_file_names.session_config

    session.config = config

    logger.info(f"Session {session.title} loaded from config")

def save_session_config(session) -> None:
    try:
        with open(session.session_config_path, "w") as f:
            json.dump(session.config, f, indent=2)
        logger.info(f"Saved config to {session.session_config_path}")
    except Exception as e:
        logger.error(f"Failed to save config to {session.session_config_path}: {e}")
        raise

def init_session_config(session) -> None:
    session.config = {
        "session_title": session.title,
        "creation_date": datetime.now().isoformat(),
        "overwrite": session.overwrite,

        "paths": {
            "session_dir": str(session.session_dir.resolve()),
            "raw_video_path": str(session.raw_video_path.resolve()),
            "annotated_video_path": str(session.annotated_video_path.resolve()),
            "landmark_data_path": str(session.landmark_data_path.resolve()),
            "analysis_data_path": str(session.analysis_data_path.resolve()),
            "session_config_path": str(session.session_config_path.resolve())
        },

        "video_metadata": {
            "width": cfg.video.width,
            "height": cfg.video,
            "fps": cfg.video
        },

        "mediapipe": {
            "model_complexity": cfg.mediapipe_prefs.model_complexity,
            "smooth_landmarks": cfg.mediapipe_prefs.smooth_landmarks,
            "min_detection_confidence": cfg.mediapipe_prefs.min_detection_confidence,
            "min_tracking_confidence": cfg.mediapipe_prefs.min_tracking_confidence
        },

        "annotation": {
            "opacity": cfg.annotation_prefs.opacity,
            "bone": {
                "colour": list(cfg.annotation_prefs.bone.colour),
                "thickness": cfg.annotation_prefs.bone.thickness
            },
            "landmark": {
                "colour": list(cfg.annotation_prefs.landmark.colour),
                "radius": cfg.annotation_prefs.landmark.radius
            },
            "reference_line": {
                "length": cfg.annotation_prefs.reference_line.length,
                "colour": list(cfg.annotation_prefs.reference_line.colour),
                "thickness": cfg.annotation_prefs.reference_line.thickness,
                "dash_factor": cfg.annotation_prefs.reference_line.dash_factor
            }
        }
    }

    save_session_config(session)
