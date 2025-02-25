# src/sessions.py
from pathlib import Path
import json
from datetime import datetime
import shutil
from typing import Dict, List, Tuple
import os

from src.config import SESSIONS_DIR, logger, MEDIAPIPE_CFG, ANNOTATION_CFG, cfg
from src.utils.video_handler import validate_raw_video
from src.utils.file_handler import validate_file_doesnt_exist

class Session:
    def __init__(self, session_title: str, original_video_path: Path, overwrite: bool = False) -> None:
        # session identifiers and root path
        self.title = session_title
        self.session_path: Path = SESSIONS_DIR / self.title

        # Video paths
        self.original_video_path = original_video_path
        self.raw_video_path: Path = self.session_path / f"raw.mp4"
        self.annotated_video_path: Path = self.session_path / f"annotated.mp4"

        # Data paths
        self.landmark_data_path: Path = self.session_path / f"landmarks.yaml"
        self.metrics_data_path: Path = self.session_path / f"metrics.json"
        self.config_path: Path = self.session_path / "config.json"

        # Data objects
        self.config: Dict = {}

        # Init methods
        self._setup_session_directory(overwrite)
        self._init_config()

    def _init_config(self) -> None:

        # Create a new session config and save it to the session directory
        self.config = {
            "session_title": self.title,
            "creation_date": datetime.now().isoformat(),
            "paths": {
                "original_video_path": str(self.original_video_path.resolve()),
                "raw_video_path": str(self.raw_video_path.resolve()),
                "annotated_video_path": str(self.annotated_video_path.resolve()),
                "landmark_data_path": str(self.landmark_data_path.resolve()),
                "metrics_data_path": str(self.metrics_data_path.resolve())
            }
        }
        self.save_config()

    def _setup_session_directory(self, overwrite: bool) -> None:
        # Check that a directory for that session doesn't already exist
        validate_file_doesnt_exist(self.session_path, "Session", overwrite=overwrite)

        # Attempt to create a session directory
        try:
            self.session_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {self.session_path}: {e}")
            raise

        # Check that the raw input video meets requirements
        if validate_raw_video(self.original_video_path):
            logger.info("Selected input video meets requirements.")

        # Attempt to clone the video to the session directory
        try:
            shutil.copy2(self.original_video_path, self.raw_video_path)
            logger.info(f"Raw video copied to {self.raw_video_path}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise

    def save_config(self) -> None:
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise

    @classmethod
    def load_existing_session(cls, session_path: Path):
        # Locate and validate the config file from selected session dir
        config_path = session_path / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"No config file found in {session_path}")

        # Attempt to load the selected config file
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise

        # Attempt to create session instance based on the existing session config
        try:
            # Create session instance without calling __init__
            instance = cls.__new__(cls)

            # session identifiers and root path
            instance.title = config.get("session_title")
            if instance.title is None:
                raise ValueError("Config missing 'session_title'")
            instance.session_path = session_path

            # Video paths
            instance.original_video_path = Path(config.get("original_video_path", ""))
            instance.raw_video_path = session_path / f"raw.mp4"
            instance.annotated_video_path = session_path / f"annotated.mp4"

            # Data paths
            instance.landmark_data_path = session_path / f"landmarks.yaml"
            instance.metrics_data_path = session_path / f"metrics.json"
            instance.config_path = config_path

            # Data objects
            instance.config = config
            instance.landmark_map = config.get("landmark_map")
            instance.landmark_connections = config.get("landmark_connections")
            print(instance.landmark_connections)
        except Exception as e:
            logger.error(f"Error initializing RowerSession from {session_path}: {e}")
            raise

        # Instance successfully loaded from the existing session
        logger.info(f"Loaded session from {session_path}")
        return instance

# Example usage:
if __name__ == "__main__":
    from src.config import DATA_DIR

    title = "athlete_1"
    original_video = DATA_DIR / "videos" / f"{title}.mp4"

    # Try to create a new session with overwrite option (set to False by default)
    new_session = Session(title, original_video, overwrite=True)
    print("New session config:", new_session.config)

    load_existing_session = False

    if load_existing_session:
        # Load an existing session
        existing_session = SESSIONS_DIR / title
        loaded_session = Session.load_existing_session(existing_session)
        print("Loaded session config:", loaded_session.config)