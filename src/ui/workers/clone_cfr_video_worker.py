import re
import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import imageio_ffmpeg as ffmpeg

from src.config import cfg, logger
from src.models.video_metadata import VideoMetadata
from src.utils.video_handler import get_total_frames
    
class CloneCFRVideoWorker(QThread):
    progress = pyqtSignal(str, int)    # (status message, progress percentage)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        input_video_path: Path,
        output_video_path: Path,
        parent=None
    ) -> None:
        super().__init__(parent)
        self.input_video_path: Path = input_video_path
        self.output_video_path: Path = output_video_path

        self.video_metadata: VideoMetadata | None = None
        self._is_canceled: bool = False

    def cancel(self):
        """Signal the thread to cancel its work."""
        self._is_canceled = True

    def _cleanup(self):
        if self.output_video_path.exists():
            self.output_video_path.unlink()
            logger.info(f"CFR cloned video remnants deleted.")

    def run(self):
        try:
            # Get the path to the ffmpeg executable.
            ffmpeg_path = ffmpeg.get_ffmpeg_exe()

            # Build the FFmpeg command.
            command = [
                ffmpeg_path,
                "-y",
                "-i", str(self.input_video_path),
                "-vsync", "cfr",
                "-r", str(cfg.video.fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-an",
                str(self.output_video_path)
            ]

            # Retrieve the total frame count for progress calculation.
            total_frames = get_total_frames(self.input_video_path)

            # Start FFmpeg with pipes so we can read progress.
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # Regular expression to extract the frame number.
            frame_regex = re.compile(r"frame=\s*(\d+)")

            # Process FFmpeg stderr output line-by-line.
            for line in iter(process.stderr.readline, ""):
                # Check for cancellation on every line.
                if self._is_canceled:
                    process.kill()
                    process.wait()
                    self._cleanup
                    self.canceled.emit()
                    return

                # Parse progress information from the output.
                if "frame=" in line:
                    match = frame_regex.search(line)
                    if match:
                        current_frame = int(match.group(1))
                        progress_percent = int((current_frame / total_frames) * 100) if total_frames > 0 else 0
                        self.progress.emit("Processing video", progress_percent)

            process.wait()
            if process.returncode != 0:
                # Read the remainder of stderr for error details.
                error_text = process.stderr.read()
                raise RuntimeError(f"FFmpeg error: {error_text}")

            self.video_metadata = VideoMetadata.from_file(self.output_video_path)

            # When processing is complete, emit finished.
            self.finished.emit()

        except Exception as e:
            error_msg = f"Error processing video: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
