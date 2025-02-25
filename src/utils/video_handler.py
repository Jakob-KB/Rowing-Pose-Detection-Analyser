import cv2
from pathlib import Path
import time
from src.config import DATA_DIR, cfg


def validate_raw_video(input_path: Path) -> bool:
    """
    Validate video file format, duration, and FPS.
    """
    if input_path.suffix.lower() != cfg.video.format:
        raise ValueError(f"Video must be {cfg.video.format}, got {input_path.suffix.lower()} instead.")

    # Open video
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f"Failed to open video at path: {str(input_path)}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / video_fps if video_fps > 0 else 0
    cap.release()

    # Validate duration
    if duration < cfg.video.min_duration or duration > cfg.video.max_duration:
        raise ValueError(f"Duration {duration:.2f} out of range [{cfg.video.min_duration}, {cfg.video.max_duration}]")

    # Validate FPS (with small tolerance)
    if abs(video_fps - cfg.video.fps) > 0.1:
        raise ValueError(f"FPS {video_fps:.2f} does not match expected {cfg.video.fps}")

    return True


def mirror_video(input_path: Path, output_path: Path, timeout: float = 5.0) -> None:
    """
    Mirrors a video horizontally and saves the output. This function blocks
    until the output file is created and has a nonzero size or until the timeout is reached.
    """
    # Open the input video file.
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f"Error opening video file: {input_path}")

    # Retrieve video properties.
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    # Define the codec and create VideoWriter object.
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Mirror the frame horizontally.
        mirrored_frame = cv2.flip(frame, 1)
        out.write(mirrored_frame)

    # Release resources.
    cap.release()
    out.release()

    # Wait for the output file to be written.
    start_time = time.time()
    while (not output_path.exists() or output_path.stat().st_size == 0) and (time.time() - start_time < timeout):
        time.sleep(0.1)


def rower_facing_right(input_path: Path, sample_frames: int = 8) -> bool:
    # Implement frame detection on the hip and ankles to tell if the rower
    # on the erg is facing left or right (not yet implemented)
    return True


if __name__ == "__main__":
    sample_input_path = DATA_DIR / "videos" / "athlete_1.mp4"
    sample_output_path = DATA_DIR / "videos" / "mirrored_athlete_1.mp4"

    mirror_video(sample_input_path, sample_output_path)

