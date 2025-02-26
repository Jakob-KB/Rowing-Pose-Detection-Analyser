from src.config import logger, SESSIONS_DIR
import re
import shutil
from pathlib import Path

min_title_length: int = 4
max_title_length: int = 32


def validate_session_title(session_title: str, overwrite: bool = False) -> (bool, str):

    # Check title is not empty
    if session_title == '':
        msg = "Session title cannot be empty."
        logger.warning(f"{msg}")
        return False, msg

    # Check title has correct length
    if len(session_title) < min_title_length or len(session_title) > max_title_length:
        msg = f"Session title must be between {min_title_length} and {max_title_length} characters long."
        logger.warning(f"{msg} Got title length of {len(session_title)} characters instead.")
        return False, msg

    # Check title only contains valid characters
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_title):
        msg = "Session title may only contain letters, digits, '-' or '_' symbols."
        logger.warning(f"{msg} Got session title '{session_title} instead.'")
        return False, msg

    # Check a session with the same title doesn't already exist
    new_session_dir = Path(SESSIONS_DIR) / session_title
    if new_session_dir.exists():
        msg = "A session with that title already exists."
        if overwrite:
            shutil.rmtree(new_session_dir)
            logger.info(f"{msg} Deleting existing session so that it can be overwritten.")
        else:
            logger.warning(f"{msg}. Either delete the existing session, set the current session to overwrite, or exit "
                           f"out and load the existing session instead.")
            return False, msg

    # Session title is valid
    logger.info(f"Session title '{session_title}' was successfully validated.")
    return True, ''