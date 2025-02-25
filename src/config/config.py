from dynaconf import Dynaconf
from pathlib import Path
import cv2
import sys
from loguru import logger
from dataclasses import dataclass

# Define project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load config from YAML and .env
cfg = Dynaconf(
    settings_files=[PROJECT_ROOT / "src" / "config" / "config.yaml"],  # Load YAML config
    envvar_prefix="APP",  # Allow ENV overrides (e.g., APP_FPS=60)
    dotenv_path=PROJECT_ROOT / ".env",  # Load from .env if exists
)

# Setup logging from config
logger.remove()
logger.add(
    sys.stdout,
    level=cfg.logging.handlers[0].get("level", "INFO"),
    format=cfg.logging.handlers[0].get("format"),
    colorize=cfg.logging.handlers[0].get("colorize", True),
)

# Paths from config
DATA_DIR = PROJECT_ROOT / cfg.dir.data
CONFIG_DIR = PROJECT_ROOT / cfg.dir.config
SESSIONS_DIR = PROJECT_ROOT / cfg.dir.sessions

# MediaPose Landmarks
LANDMARK_MAP_R = {
    "ear": 8,
    "shoulder": 12,
    "elbow": 14,
    "wrist": 16,
    "hand": 20,
    "hip": 24,
    "knee": 26,
    "ankle": 28,
}

LANDMARK_CONNECTIONS_R = [
    (8, 12),   # Ear to shoulder
    (12, 14),  # Shoulder to Elbow
    (14, 16),  # Elbow to Wrist
    (16, 20),  # Wrist to Hand
    (12, 24),  # Shoulder to Hip
    (24, 26),  # Hip to Knee
    (26, 28)   # Knee to Ankle
]

# Annotated video config
ANNOTATION_CFG = {
    "landmark_point_colour": (255, 0, 0),
    "landmark_point_radius": 9,
    "skeleton_bone_colour": (0, 255, 0),
    "skeleton_bone_width": 2,
    "skeleton_opacity": 0.5,
    "landmark_connections": [
        (8, 12),   # Ear to shoulder
        (12, 14),  # Shoulder to Elbow
        (14, 16),  # Elbow to Wrist
        (16, 20),  # Wrist to Hand
        (12, 24),  # Shoulder to Hip
        (24, 26),  # Hip to Knee
        (26, 28)   # Knee to Ankle
    ]
}

MEDIAPIPE_CFG = {
    "model_complexity": 2,
    "smooth_landmarks": True,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
    "landmark_map": {
        "ear": 8,
        "shoulder": 12,
        "elbow": 14,
        "wrist": 16,
        "hand": 20,
        "hip": 24,
        "knee": 26,
        "ankle": 28,
    }
}