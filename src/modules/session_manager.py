# src/modules/session_manager.py

import shutil

from src.models.annotation_preferences import AnnotationPreferences
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session import Session
from src.models.session_files import SessionFiles
from src.models.video_metadata import VideoMetadata

from pathlib import Path
from src.config import cfg, logger

from src.config import SESSIONS_DIR

class SessionManager:
    @staticmethod
    def create_session(
            session_title: str,
            original_video_path: Path,
            mediapipe_preferences: MediapipePreferences = MediapipePreferences(),
            annotation_preferences: AnnotationPreferences = AnnotationPreferences(),
            overwrite: bool = False) -> Session:

        session_directory = SESSIONS_DIR / session_title
        files = SessionFiles.from_session_directory(session_directory=session_directory)

        if session_directory.exists():
            if overwrite:
                shutil.rmtree(session_directory)
                logger.info(f"Session {session_title} already exists, deleting for overwrite.")
            else:
                raise FileExistsError(f"Session '{session_title}' already exists.")
            
        session = Session(
            title=session_title,
            original_video_path=original_video_path,
            directory=session_directory,
            files=files,
            video_metadata=None,
            mediapipe_preferences=mediapipe_preferences,
            annotation_preferences=annotation_preferences
        )

        try:
            # Create the session directory
            session_directory.mkdir(parents=True, exist_ok=False)

            # Save config to the session directory
            with open(session.files.session_config, "w") as f:
                f.write(session.model_dump_json(indent=4))
            logger.info(f"Session created and saved to {session.directory}.")

            return session
        except Exception as e:
            raise Exception(f"Error creating session: {e}")

    @staticmethod
    def save_session(session: Session) -> None:
        with open(session.files.session_config, "w") as f:
            f.write(session.model_dump_json(indent=4))
        logger.info(f"Session config saved for '{session.title}'.")

    @staticmethod
    def update_session(session: Session) -> None:
        if not session.directory.exists():
            return
        if session.files.raw_video.exists():
            session.video_metadata = VideoMetadata.from_file(session.files.raw_video)
            logger.info(f"Session video metadata updated for '{session.title}'.")

    @staticmethod
    def load_session(session_directory: Path, progress_callback=None) -> Session:
        """
        Loads a session configuration from a JSON file in the given session directory.
        """
        config_file = session_directory / cfg.session.files.session_config

        if progress_callback:
            progress_callback("Loading session", 0)

        if not config_file.exists():
            raise FileNotFoundError("Unable to find config file for the selected session.")

        try:
            with open(config_file, "r") as f:
                data = f.read()
            session = Session.model_validate_json(data)
            session.video_metadata = VideoMetadata.from_dict(session.video_metadata)
            logger.info(f"Session loaded from {config_file}.")

            if progress_callback:
                progress_callback("Loading session", 100)

            return session
        except Exception as e:
            logger.error(f"Error loading session configuration: {e}")
            raise

    @staticmethod
    def delete_session(session: Session) -> None:
        expected_session_files = session.files.expected_files()
        all_session_files = [file.name for file in session.directory.iterdir()]

        for file in all_session_files:
            if file not in expected_session_files:
                raise FileExistsError(
                    f"Foreign file found in session directory, session will have to be deleted manually: {file}"
                )

        shutil.rmtree(session.directory)
        logger.info(f"Session '{session.title}' has been deleted from {session.directory}")
