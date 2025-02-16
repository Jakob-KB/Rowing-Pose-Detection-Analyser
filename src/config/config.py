import logging
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
        print(f"⚠️ Warning: Config file {config_path} not found. Using defaults.")
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
SRC_DIR = get_path("src")
LOGS_DIR = get_path("logs")

# Ensure required directories exist
for directory in [
    DATA_DIR,
    CONFIG_DIR,
    REPORTS_DIR,
    LOGS_DIR
]:
    os.makedirs(directory, exist_ok=True)

# Configure logging
logger.remove()  # Remove default Loguru handlers
log_handlers = config.get("logging", {}).get("handlers", [])

for handler in log_handlers:
    sink = handler.get("sink", "stdout")

    if sink.lower() == "stdout":
        sink = sys.stdout
        logger.add(
            sys.stdout,
            level=handler.get("level", "INFO").upper(),
            format=handler.get("format", "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"),
            colorize=handler.get("colorize", False)
        )
    elif sink.lower() == "stderr":
        sink = sys.stderr
        logger.add(
            sys.stderr,
            level=handler.get("level", "INFO").upper(),
            format=handler.get("format", "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"),
            colorize=handler.get("colorize", False),
            rotation=handler.get("rotation", None),
            retention=handler.get("retention", None),
        )
