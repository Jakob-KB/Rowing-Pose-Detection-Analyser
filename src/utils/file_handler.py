# src/utils/file_handler.py
import shutil
from pathlib import Path
from typing import List
import mimetypes
import os

from src.config import logger

def validate_file_exists(file_path: Path, var_name: str = "File") -> None:
    """
    Check if a file exists.
    """
    file_exists: bool = file_path.exists()

    if file_exists is True:
        logger.info(f"{var_name} was found at {file_path}")
    elif file_exists is False:
        raise FileNotFoundError(f"Unable to find {var_name} at {file_path}")


def validate_file_doesnt_exist(file_path: Path, var_name: str = "File", overwrite: bool = False) -> None:
    """
    Check file doesn't already exist, if it does delete it if directed.
    """
    file_exists: bool = file_path.exists()

    if file_exists is True and overwrite is True:
        logger.warning(f"{var_name} already exists at {file_path}. Deleting so it can be overwritten.")
        if file_path.is_file():
            os.remove(file_path)
        elif file_path.is_dir():
            shutil.rmtree(file_path)
    elif file_exists is True and overwrite is False:
        raise FileExistsError(f"{var_name} already exists at {file_path}. Delete or overwrite it instead.")
    elif file_exists is False:
        logger.info(f"{var_name} clear as {file_path} doesn't exist.")


def validate_directory(directory: Path, create_if_missing: bool = False) -> bool:
    """Check if a directory exists or create it if requested."""
    if directory.is_dir():
        logger.info(f"Successfully identified directory: {directory}")
        return True
    if create_if_missing:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Successfully identified/created directory: {directory}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
    logger.error(f"Failed to identified directory: {directory}")
    return False


def get_videos_from_path(videos_path: Path, video_type: str = "mp4") -> List[Path]:
    """
    Retrieve all video files of a specified type from a given directory.
    """
    if not videos_path.is_dir():
        raise ValueError(f"Invalid directory: {videos_path}")

    videos = []
    for file in videos_path.iterdir():
        if file.is_file():
            # Guess the MIME type to ensure it's a valid video format
            mimetype, _ = mimetypes.guess_type(file)
            if mimetype and mimetype.startswith("video/") and file.suffix.lower() == f".{video_type}":
                videos.append(file)

    return videos


if __name__ == "__main__":
    my_file_path = Path("test3.txt")
    validate_file_exists(my_file_path)