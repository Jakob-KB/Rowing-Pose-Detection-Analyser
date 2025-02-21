from pathlib import Path
from typing import List
import mimetypes

from src.config import logger


def validate_file(file_path: Path, create_if_missing: bool = False) -> bool:
    """
    Check if a file exists and is a regular file. Optionally, create the file
    (and its parent directories) if it is missing.
    """
    if file_path.is_file():
        logger.info(f"Successfully identified file: {file_path}")
        return True

    if create_if_missing:
        try:
            # Ensure the parent directory exists
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created parent directory: {file_path.parent}")
            # Create the file (or update the modified time if it already exists)
            file_path.touch(exist_ok=True)
            logger.info(f"Successfully created file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")

    logger.error(f"Failed to identify file: {file_path}")
    return False


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
