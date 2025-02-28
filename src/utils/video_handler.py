import cv2
from pathlib import Path
import time
from src.config import DATA_DIR, cfg, logger

def validate_raw_video(input_path: Path) -> (bool, str):
    """
    Validate video_metadata file format, duration, and FPS.
    """

    # Check video_metadata format
    if input_path.suffix.lower() != str("." + cfg.video_metadata.format):
        msg = f"Video format must be {cfg.video_metadata.format}."
        logger.warning(f"{msg} Got {input_path.suffix.lower()} instead.")
        return False, msg

    # Attempt to open video_metadata
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        msg = f"Failed to open video_metadata."
        logger.warning(f"{msg} At path: {str(input_path)}")
        return False, msg

    # Get video_metadata metadata
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / video_fps if video_fps > 0 else 0
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()

    # Check video_metadata fps, with small tolerance
    if abs(video_fps - cfg.video_metadata.fps) > 0.1:
        msg = f"Video must be approx {cfg.video_metadata.fps} fps."
        logger.warning(f"{msg} Got {video_fps} fps instead.")
        return False, msg

    # Check video_metadata duration
    if duration < cfg.video_metadata.min_duration or duration > cfg.video_metadata.max_duration:
        msg = f"Video must be between {cfg.video_metadata.min_duration} and {cfg.video_metadata.max_duration} seconds long."
        logger.warning(f"{msg} Got {duration} seconds instead.")
        return False, msg

    # Check video_metadata dimensions
    if width != cfg.video_metadata.width or height != cfg.video_metadata.height:
        msg = f"Video have dimensions {cfg.video_metadata.width}x{cfg.video_metadata.height}."
        logger.warning(f"{msg} Got dimensions {width}x{height} instead.")
        return False, msg

    # Video is valid
    logger.info(f"Video was successfully validated.")
    return True, ""

def mirror_video(input_path: Path, output_path: Path, timeout: float = 5.0) -> None:
    """
    Mirrors a video_metadata horizontally and saves the output. This function blocks
    until the output file is created and has a nonzero size or until the timeout is reached.
    """
    # Open the input video_metadata file.
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f"Error opening video_metadata file: {input_path}")

    # Retrieve video_metadata properties.
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
