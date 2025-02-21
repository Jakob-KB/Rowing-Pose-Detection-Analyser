import sys
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

# Define project root dynamically
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "src" / "config" / "config.yaml"


# Load YAML config
def load_config(config_path):
    """Load configuration from YAML file."""
    if config_path.exists():
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    else:
        print("Warning: Config not found.")
        return {}


config = load_config(CONFIG_FILE)


# Extract paths from config
def get_path(key):
    """Helper function to fetch paths from config."""
    return PROJECT_ROOT / Path(config.get("paths", {}).get(key, ""))


# Project Paths
DATA_DIR = get_path("data")
CONFIG_DIR = get_path("config")
REPORTS_DIR = get_path("reports")
LOGS_DIR = get_path("logs")

# Ensure required directories exist
for directory in [DATA_DIR, CONFIG_DIR, REPORTS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Add main logger
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    colorize=True,
)

# MediaPose Landmarks
RIGHT_FACING_LANDMARKS = {
    "EarR": 8,
    "ShoulderR": 12,
    "ElbowR": 14,
    "HandR": 16,
    "MidFingersR": 20,
    "HipR": 24,
    "KneeR": 26,
    "AnkleR": 28
}
