# src/config/config.py

import sys
from pathlib import Path

from dynaconf import Dynaconf
from loguru import logger


# Define project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load config from YAML and .env
cfg = Dynaconf(
    settings_files=[PROJECT_ROOT / "src" / "config" / "config.yaml"],
    envvar_prefix="APP",
    dotenv_path=PROJECT_ROOT / ".env",
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
DATA_DIR = PROJECT_ROOT / cfg.directories.data
SRC_DIR = PROJECT_ROOT / cfg.directories.src
SESSIONS_DIR = PROJECT_ROOT / cfg.directories.sessions
