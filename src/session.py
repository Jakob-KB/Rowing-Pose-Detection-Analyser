# src/sessions.py
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
import imageio_ffmpeg as ffmpeg

from src.utils.session_config_io import init_session_config, apply_config
from src.utils.file_handler import check_session_filepath_exists
from src.config import SESSIONS_DIR, cfg, logger


class Session:
    title: str
    overwrite: bool

    session_dir: Path
    session_config_path: Path
    raw_video_path: Path
    landmark_data_path: Path
    analysis_data_path: Path
    annotated_video_path: Path

    def __init__(
        self, session_title: str,
        overwrite: bool = False,
        temp_video_path: Optional[Path] = None,
        config: Optional[Dict] = None
    ) -> None:
        self.title = session_title
        self.overwrite = overwrite

        self.session_dir = Path(SESSIONS_DIR) / session_title
        self.session_config_path = self.session_dir / cfg.session_file_names.session_config
        self.raw_video_path = self.session_dir / cfg.session_file_names.raw_video
        self.landmark_data_path = self.session_dir / cfg.session_file_names.landmark_data
        self.analysis_data_path = self.session_dir / cfg.session_file_names.analysis_data
        self.annotated_video_path = self.session_dir / cfg.session_file_names.annotated_video

        print("About to check config")
        if config is not None:
            print("Config is not NONE")
            apply_config(self, config)
        else:
            if self.session_dir.exists():
                if not self.overwrite:
                    logger.error("A session directory with this name already exists.")
                    raise FileExistsError("A session directory with this name already exists.")
                else:
                    shutil.rmtree(self.session_dir)

            self._setup_session_directory(temp_video_path)
            init_session_config(self)

    def _setup_session_directory(self, temp_video_path: Path) -> None:
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {self.session_dir}: {e}")
            raise

        try:
            # Get ffmpeg binary path from imageio package to clone raw video with CFR
            ffmpeg_path = ffmpeg.get_ffmpeg_exe()

            command = [
                ffmpeg_path, "-y" if self.overwrite else "-n",
                "-i", str(temp_video_path),
                "-vsync", "cfr",
                "-r", str(cfg.video.fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-an",
                str(self.raw_video_path)
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Raw video copied to {self.raw_video_path}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise

    def is_valid_to_view(self) -> Tuple[bool, str]:
        # Check all files exist within the
        paths_to_check = [
            (self.session_dir, "session directory"),
            (self.session_config_path, "session config"),
            (self.raw_video_path, "raw video"),
            (self.landmark_data_path, "landmark data"),
            # (self.analysis_data_path, "analysis data"),
            (self.annotated_video_path, "annotated video")
        ]

        for path, description in paths_to_check:
            valid, msg = check_session_filepath_exists(path, description, self.title)
            if not valid:
                return False, msg

        return True, ""

    @classmethod
    def create(cls, session_title: str, original_video_path: Path, overwrite: bool = False) -> "Session":
        """Alternative constructor for creating a new session."""
        return cls(session_title, overwrite, original_video_path, config=None)

    @classmethod
    def load(cls, session_dir) -> "Session":
        from pathlib import Path
        session_dir = Path(session_dir)  # Ensure it's a Path object

        print("opened class method load")
        config_file_path = session_dir / cfg.session_file_names.session_config

        print(f"Looking for session config file at: {config_file_path}")

        if not config_file_path.exists():
            print("Config file does not exist!")
            raise FileNotFoundError(f"No config file found at {config_file_path}")

        try:
            with open(config_file_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
            raise

        print("Config file loaded successfully")

        session = cls.__new__(cls)
        session.title = config.get("session_title", "Unknown")
        session.overwrite = config.get("overwrite", False)
        session.session_dir = session_dir
        session.session_config_path = config_file_path
        session.raw_video_path = session_dir / cfg.session_file_names.annotated_video
        session.landmark_data_path = session_dir / cfg.session_file_names.landmark_data
        session.analysis_data_path = session_dir / cfg.session_file_names.analysis_data
        session.annotated_video_path = session_dir / cfg.session_file_names.annotated_video

        print("Returning session object")
        return session


# Example usage:
if __name__ == "__main__":
    from src.config import DATA_DIR

    title = "athlete_1"
    original_video = DATA_DIR / "videos" / f"{title}.mp4"

    # Creating a new session:
    new_session = Session.create(title, original_video, overwrite=True)
    print("New session config:", new_session.config)

    load_existing_session = False

    if load_existing_session:
        # Loading an existing session:
        existing_session_path = SESSIONS_DIR / title
        loaded_session = Session.load(existing_session_path)
        print("Loaded session config:", loaded_session.config)
