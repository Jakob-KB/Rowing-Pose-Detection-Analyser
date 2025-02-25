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
RIGHT_LANDMARKS = {
    "Ear": 8,
    "Shoulder": 12,
    "Elbow": 14,
    "Hand": 16,
    "Fingers": 20,
    "Hip": 24,
    "Knee": 26,
    "Ankle": 28,
}

LEFT_LANDMARKS = {
    "Ear": 7,
    "Shoulder": 11,
    "Elbow": 13,
    "Hand": 15,
    "Fingers": 19,
    "Hip": 23,
    "Knee": 25,
    "Ankle": 27,
}
