# src/sessions.py
from pathlib import Path
import json
from datetime import datetime
import shutil
from typing import Dict
import os
import cv2

from src.config import SESSIONS_DIR, logger
from src.utils.video_handler import validate_raw_video
from src.utils.file_handler import check_path_is_clear

class Session:
    def __init__(self, session_title: str, temp_video_path: Path, overwrite: bool = False) -> None:
        # session identifiers and root path
        self.title = session_title
        self.session_path: Path = SESSIONS_DIR / self.title
        self.overwrite = overwrite

        # Check that a session folder associated with the title doesn't already exist
        valid, msg = self.validate_paths_and_files()
        if not valid:
            logger.error(msg)
            raise

        # Video paths
        self.raw_video_path: Path = self.session_path / f"raw.mp4"
        self.annotated_video_path: Path = self.session_path / f"annotated.mp4"

        # Data paths
        self.landmark_data_path: Path = self.session_path / f"landmarks.yaml"
        self.metrics_data_path: Path = self.session_path / f"metrics.json"
        self.config_path: Path = self.session_path / "config.json"

        # Data objects
        self.config: Dict = {}

        # Init methods
        self._setup_session_directory()
        self._clone_temp_video_to_session_directory(temp_video_path)
        self._init_config()

    def _init_config(self) -> None:

        # Create a new session config and save it to the session directory
        self.config = {
            "session_title": self.title,
            "creation_date": datetime.now().isoformat(),
            "overwrite": self.overwrite,
            "paths": {
                "raw_video_path": str(self.raw_video_path.resolve()),
                "annotated_video_path": str(self.annotated_video_path.resolve()),
                "landmark_data_path": str(self.landmark_data_path.resolve()),
                "metrics_data_path": str(self.metrics_data_path.resolve())
            }
        }
        self.save_config()

    def _setup_session_directory(self) -> None:
        # Attempt to create a session directory
        try:
            self.session_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {self.session_path}: {e}")
            raise

    def _clone_temp_video_to_session_directory(self, temp_video_path: Path):
        # Check that the raw input video meets requirements
        valid, error_msg = validate_raw_video(temp_video_path)
        if not valid:
            # Do something to now create the instance, but do not hold the program
            print("video not valid")
            ...

        # Attempt to clone the video to the session directory
        try:
            shutil.copy2(temp_video_path, self.raw_video_path)
            logger.info(f"Raw video copied to {self.raw_video_path}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise

        # Check that the raw video was saved to the session directory successfully (try to open it)
        # Attempt to open video
        cap = cv2.VideoCapture(str(self.raw_video_path))
        if not cap.isOpened():
            msg = f"Failed to open video."
            logger.warning(f"{msg} At path: {self.raw_video_path}")
            return False, msg
        cap.release()

        # Now that the raw video is confirmed to be good, delete the temp video
        os.remove(temp_video_path)

    def save_config(self) -> None:
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise

    def validate_paths_and_files(self) -> (bool, str):
        # Check that a directory for that session doesn't already exist
        valid, msg = check_path_is_clear(self.session_path, "Session", overwrite=self.overwrite)
        if not valid:
            return valid, msg

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
            instance.overwrite = config.get("overwrite")

            # Video paths
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