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
ANALYSES_DIR = PROJECT_ROOT / cfg.dir.analyses

# MediaPose Landmarks
LANDMARK_MAP_R = {
    "Ear": 8,
    "Shoulder": 12,
    "Elbow": 14,
    "Wrist": 16,
    "Hand": 20,
    "Hip": 24,
    "Knee": 26,
    "Ankle": 28,
}

LANDMARK_MAP_L = {
    "Ear": 7,
    "Shoulder": 11,
    "Elbow": 13,
    "Wrist": 15,
    "Hand": 19,
    "Hip": 23,
    "Knee": 25,
    "Ankle": 27,
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