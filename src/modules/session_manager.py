# src/modules/session_manager.py

import shutil
from pathlib import Path

from src.config import cfg, logger
from src.models.operation_controls import OperationControls
from src.models.session import Session
from src.models.video_metadata import VideoMetadata
from src.utils.file_handler import check_session_file_exists
from src.utils.video_handler import clone_cfr_video_to_path


class SessionManager:

    @staticmethod
    def create_session(session_title: str, original_video_path: Path, overwrite: bool = False) -> Session:
        return Session.create(
            session_title=session_title,
            original_video_path=original_video_path,
            overwrite=overwrite,
        )

    @staticmethod
    def setup_session_directory(session: Session, operation_controls: OperationControls) -> None:
        # Handle existing session directory.
        if session.directory.exists():
            if not operation_controls.overwrite:
                logger.error("A session directory with this name already exists.")
                raise FileExistsError("A session directory with this name already exists.")
            else:
                shutil.rmtree(session.directory)
                logger.info(f"Existing session directory {session.directory} removed due to overwrite being set.")

        session.directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Session directory created at {session.directory}.")

        # Clone the original video to the session directory with CFR of 30 fps
        clone_cfr_video_to_path(
            session.original_video_path,
            session.files.raw_video,
            operation_controls=operation_controls
        )

        # Configure metadata for any video associated with the session.
        session.video_metadata = VideoMetadata.from_file(session.files.raw_video)

        # Save session configuration.
        try:
            with open(session.files.session_config, "w") as f:
                f.write(session.model_dump_json(indent=4))
            logger.info(f"Session configuration saved to {session.files.session_config}.")
        except Exception as e:
            raise FileNotFoundError(f"Error saving session configuration: {e}")

    @staticmethod
    def load_session(session_directory: Path) -> Session:
        """
        Loads a session configuration from a JSON file in the given session directory.
        """
        config_file = session_directory / cfg.session.files.session_config

        valid, msg = check_session_file_exists(config_file, "config file", session_directory.name)
        if not valid:
            raise FileNotFoundError(msg)

        try:
            with open(config_file, "r") as f:
                data = f.read()
            session = Session.model_validate_json(data)
            session.video_metadata = VideoMetadata.from_dict(session.video_metadata)
            logger.info(f"Session loaded from {config_file}.")
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
                raise FileExistsError(f"Foreign file found in session directory, session will have to be deleted"
                                        f"manually: {file}")

        shutil.rmtree(session.directory)
        logger.info(f"Session '{session.title}' has been deleted from your session directory at {session.directory}")


def main():
    from src.config import DATA_DIR
    from src.utils.progress_callback import progress_callback

    sample_session_title = "sample_session"
    sample_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

    session_manager = SessionManager()

    sample_session = session_manager.create_session(
        session_title=sample_session_title,
        original_video_path=sample_video_path,
        overwrite=True
    )

    session_manager.setup_session_directory(
        session=sample_session,
        progress_callback=progress_callback
    )



    input(f"Press any key to delete '{sample_session_title}'...")

    session_manager.delete_session(sample_session)

if __name__ == "__main__":
    main()
