# src/modules/session_manager.py
import shutil
import subprocess
from pathlib import Path
import imageio_ffmpeg as ffmpeg

from src.models.landmark_data import LandmarkData
from src.config import cfg, logger
from src.models.session import Session
import yaml

class SessionManager:
    @staticmethod
    def new_session(session_title: str, original_video_path: Path, overwrite: bool = False) -> Session:

        session = Session.create(
            session_title=session_title,
            original_video_path=original_video_path
        )

        # Check if the session directory exists.
        if session.session_dir.exists():
            if not overwrite:
                logger.error("A session directory with this name already exists.")
                raise FileExistsError("A session directory with this name already exists.")
            else:
                shutil.rmtree(session.session_dir)
                logger.info(f"Existing session directory {session.session_dir} removed due to overwrite=True.")

        # Create the session directory.
        try:
            session.session_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Session directory created at {session.session_dir}.")
        except Exception as e:
            logger.error(f"Failed to create session directory {session.session_dir}: {e}")
            raise

        # Process the original video: clone it to raw video using ffmpeg.
        try:
            ffmpeg_path = ffmpeg.get_ffmpeg_exe()
            command = [
                ffmpeg_path,
                "-y" if overwrite else "-n",
                "-i", str(original_video_path),
                "-vsync", "cfr",
                "-r", str(cfg.video.fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-an",
                str(session.files.raw_video)
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Raw video processed and saved with CFR to {session.session_dir / 'raw_video_path.mp4'}.")
        except Exception as e:
            logger.error(f"Error while processing raw video: {e}")
            raise

        # Save the session configuration to a JSON file in the session directory.
        try:
            with open(session.files.session_config, "w") as f:
                # Use model_dump_json with indentation for pretty printing
                f.write(session.model_dump_json(indent=4))
            logger.info(f"Session configuration saved to {session.files.session_config}.")
        except Exception as e:
            logger.error(f"Error saving session configuration: {e}")
            raise

        return session

    @staticmethod
    def load_existing_session(session_dir: Path) -> Session:
        """
        Loads a session configuration from a JSON file in the given session directory.
        """
        config_file = session_dir / cfg.session.files.session_config

        if not config_file.exists():
            raise FileNotFoundError(f"Session configuration file not found at {config_file}")

        try:
            with open(config_file, "r") as f:
                data = f.read()
            session = Session.model_validate_json(data)
            logger.info(f"Session loaded from {config_file}.")
            return session
        except Exception as e:
            logger.error(f"Error loading session configuration: {e}")
            raise

    @staticmethod
    def save_landmarks_to_session(session: Session, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()

        try:
            with open(session.files.landmark_data, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {session.files.landmark_data}")
        except Exception as e:
            logger.error(f"Error saving landmark data: {e}")
            raise Exception()

    @staticmethod
    def load_landmarks_from_session(session: Session) -> LandmarkData:
        if not session.files.landmark_data.exists():
            raise FileNotFoundError(f"Landmark file not found at {session.files.landmark_data}")

        with open(session.files.landmark_data, "r") as f:
            data_dict = yaml.safe_load(f)

        landmark_data = LandmarkData.from_dict(data_dict)
        logger.info(f"Landmark data loaded from {session.files.landmark_data}")
        return landmark_data