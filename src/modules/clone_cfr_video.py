from pathlib import Path
import imageio_ffmpeg as ffmpeg
import subprocess
import time

from src.config import cfg, logger
from src.models.video_metadata import VideoMetadata
from src.utils.status_callback import status_callback
from src.utils.exceptions import ProcessCancelled




class CloneCFRVideo:
    _is_cancelled = False
    cancellation_message = "Cloning CFR video cancelled."
    success_message = "Cloned CFR video successfully."

    def run(self, input_video_path: Path, output_video_path: Path, status=status_callback) -> VideoMetadata:
        self._is_cancelled = False

        # Update initial status.
        if status:
            status(code="0001", message="Checking location of original video.")

        if not output_video_path.exists():
            raise FileNotFoundError(f"Failed to find original video file.")

        if self._is_cancelled:
            raise ProcessCancelled("")


        # Build the FFmpeg command.
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg_path,
            "-y",
            "-i", str(input_video_path),
            "-loglevel", "quiet",
            "-vsync", "cfr",
            "-r", str(cfg.video.fps),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-an",
            str(output_video_path)
        ]

        # Launch the process.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Instead of process.wait(), poll the process to allow cancellation and periodic status updates.
        while process.poll() is None:
            if self._is_cancelled:
                process.terminate()
                if status:
                    msg, progress, code = status("Cancelled", 0, -1)
                    logger.info(f"Status update: {msg} | Progress: {progress}% | Code: {code}")
                raise Exception("Pipeline cancelled")
            if status:
                # Here we simply report an intermediate progress (for example, 50%).
                msg, progress, code = status("Cloning video...", 50, 100)
                logger.info(f"Status update: {msg} | Progress: {progress}% | Code: {code}")
            time.sleep(1)

        # Gather any output.
        stdout, stderr = process.communicate()

        # Check for errors.
        if process.returncode != 0:
            if status:
                msg, progress, code = status("FFmpeg error", 100, -1)
                logger.info(f"Status update: {msg} | Progress: {progress}% | Code: {code}")
            raise RuntimeError(f"FFmpeg error: {stderr.decode()}")

        # Final status update.
        if status:
            msg, progress, code = status("Video cloning complete", 100, 0)
            logger.info(f"Status update: {msg} | Progress: {progress}% | Code: {code}")

        logger.info(f"Raw video processed and cloned with CFR to {output_video_path}")
        return VideoMetadata.from_file(output_video_path)

    def cancel(self):
        self._is_cancelled = True

