# src/utils/video_handler.py

import cv2
from pathlib import Path
from typing import Tuple
import time
import imageio_ffmpeg as ffmpeg
import re

import subprocess
from src.config import cfg, logger
from src.models.operation_controls import OperationControls
from src.utils.exceptions import CancellationException

def validate_raw_video(video_path: Path) -> Tuple[bool, str]:
    """
    Validate video_metadata file format, duration, and FPS.
    """

    # Check video_metadata format
    if video_path.suffix.lower() != str("." + cfg.video_metadata.format):
        msg = f"Video format must be {cfg.video_metadata.format}."
        logger.warning(f"{msg} Got {video_path.suffix.lower()} instead.")
        return False, msg

    # Attempt to open video_metadata
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        msg = f"Failed to open video_metadata."
        logger.warning(f"{msg} At path: {str(video_path)}")
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

def mirror_video(video_path: Path, output_path: Path, timeout: float = 5.0) -> None:
    """
    Mirrors a video_metadata horizontally and saves the output. This function blocks
    until the output file is created and has a nonzero size or until the timeout is reached.
    """
    # Open the input video_metadata file.
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Error opening video_metadata file: {video_path}")

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

def get_total_frames(video_path: Path) -> int:
    """Returns the total number of frames in a videos file."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total

def clone_cfr_video_to_path(
        input_video_path: Path,
        output_video_path: Path,
        operation_controls: OperationControls
) -> None:
    # Clone the original video to the session directory with CFR at 30fps.
    total_frames = get_total_frames(input_video_path)

    ffmpeg_path = ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_path,
        "-y" if operation_controls.overwrite else "-n",
        "-i", str(input_video_path),
        "-vsync", "cfr",
        "-r", str(cfg.video.fps),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-an",
        str(output_video_path)
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    frame_regex = re.compile(r"frame=\s*(\d+)")

    # Read FFmpeg output live.
    for line in iter(process.stderr.readline, ""):
        # Check for cancellation on each line
        if operation_controls.cancellation_token and operation_controls.cancellation_token.cancelled:
            logger.info("Cancellation requested, terminating FFmpeg process.")
            process.kill()
            process.wait()
            raise CancellationException("Session setup cancelled by user.")

        if "frame=" in line:
            match = frame_regex.search(line)
            if match:
                try:
                    processed_frames = int(match.group(1))
                    progress = (processed_frames / total_frames) * 100
                    if operation_controls.progress_callback:
                        operation_controls.progress_callback("Setting up session", progress)
                except ValueError:
                    pass

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {process.stderr.read()}")

    logger.info(f"Raw video processed and cloned with CFR to {output_video_path}")
