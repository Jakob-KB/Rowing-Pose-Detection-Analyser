import shutil
from pathlib import Path
from src.models.session import Session
from src.models.video_metadata import VideoMetadata
from src.config import logger, cfg


def load_session(session_directory: Path) -> Session:
    """
    Loads a session configuration from a JSON file in the given session directory.
    """
    config_file = session_directory / cfg.session.files.session_config

    if not config_file.exists():
        raise FileNotFoundError("Unable to find config file for the selected session.")

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

def delete_session(session: Session | Path) -> None:
    if isinstance(session, Path):
        try:
            session = load_session(session)
        except Exception as e:
            raise Exception(f"Failed to load session for deletion, will need to be deleted manually: {e}")

    expected_session_files = session.files.expected_files()
    all_session_files = [file.name for file in session.directory.iterdir()]

    for file in all_session_files:
        if file not in expected_session_files:
            raise FileExistsError(
                f"Session will have to be deleted manually, foreign file found in session directory: {file}"
            )

    shutil.rmtree(session.directory)
    logger.info(f"Session '{session.title}' has been deleted from {session.directory}")
