import cv2
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from src.config import DATA_DIR, logger


# Function to extract frames from a video
def extract_frames(video_path: Path, save_folder: Path, frame_interval: int):
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return 0  # No frames extracted

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path}")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        logger.error(f"Total frame count is 0 for video: {video_path}")
        return 0

    # Create folder for extracted frames
    save_folder.mkdir(parents=True, exist_ok=True)

    logger.info(f"Processing {video_path.name}: {total_frames} total frames, extracting every {frame_interval} frames.")

    extracted_count = 0  # Track frames extracted for this video

    with tqdm(total=total_frames, desc=f"Processing {video_path.name}") as pbar:
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Save frame every 'frame_interval' frames
            if frame_count % frame_interval == 0:
                frame_filename = save_folder / f"frame_{frame_count:04d}.jpg"
                cv2.imwrite(str(frame_filename), frame)
                extracted_count += 1

            frame_count += 1
            pbar.update(1)

    cap.release()
    logger.info(
        f"Finished extracting frames from {video_path.name}. Extracted {extracted_count} frames. Saved in {save_folder}")
    return extracted_count  # Return count for this video


def main():
    # Load metadata file
    metadata_path = DATA_DIR / "video_metadata.csv"
    metadata = pd.read_csv(metadata_path)

    # Define frame extraction settings
    OUTPUT_DIR = DATA_DIR / "frames"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Track total frames extracted across all videos
    grand_total_extracted = 0

    # Loop through each video and extract frames
    for _, row in metadata.iterrows():
        video_file = DATA_DIR / "videos" / row["filename"]
        if not video_file.exists():
            logger.error(f"Skipping missing file: {video_file}")
            continue

        save_path = OUTPUT_DIR / video_file.stem

        num_frames = row["frames"]
        frame_interval = max(num_frames // 100, 5)  # Ensures at least 100 frames per video

        logger.info(f"Starting frame extraction for {row['filename']} | Interval: {frame_interval} frames.")
        extracted_frames = extract_frames(video_file, save_path, frame_interval)

        grand_total_extracted += extracted_frames  # Add to grand total

    logger.info(f"Frame extraction complete! Total frames extracted: {grand_total_extracted}")

if __name__ == "__main__":
    main()
