# src/data/extract_video_metadata.py
from pathlib import Path
import pandas as pd
import cv2
import mimetypes

from src.config import PROJECT_ROOT, DATA_DIR, logger


def get_video_length(video_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return frame_count


def update_video_metadata(videos_path: Path, videos_metadata_path: Path):
    # Load existing metadata CSV or create a new one if missing
    try:
        df = pd.read_csv(videos_metadata_path)
        if df.empty:
            logger.warning("Metadata file is empty. Creating a new DataFrame.")
            df = pd.DataFrame(columns=["filename", "frames"])
    except (pd.errors.EmptyDataError, FileNotFoundError):
        logger.error("Metadata file is missing or corrupted. Creating a new DataFrame.")
        df = pd.DataFrame(columns=["filename", "frames"])

    # Ensure 'frames' column exists
    if "frames" not in df.columns:
        df["frames"] = pd.NA  # Initialize the column with NaN values

    for video in videos_path.iterdir():
        if video.is_file():  # Ensure item is a file
            mime_type, _ = mimetypes.guess_type(str(video))

            if mime_type and mime_type.startswith("video"):
                video_length = get_video_length(video)

                if video.name in df["filename"].values:
                    # Update existing entry
                    df.loc[df["filename"] == video.name, "frames"] = video_length
                else:
                    # Append new entry
                    new_entry = pd.DataFrame({"filename": [video.name], "frames": [video_length]})
                    df = pd.concat([df, new_entry], ignore_index=True)

    # Save updated metadata
    df.to_csv(videos_metadata_path, index=False)
    logger.info(f"Updated metadata saved to {Path(videos_metadata_path).relative_to(PROJECT_ROOT)}")


def main():
    videos_dir = DATA_DIR / "videos"
    metadata_file = DATA_DIR / "video_metadata.csv"
    update_video_metadata(videos_dir, metadata_file)


if __name__ == "__main__":
    main()
