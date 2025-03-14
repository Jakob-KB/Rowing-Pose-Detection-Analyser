import re
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
import imageio_ffmpeg as ffmpeg

from src.config import cfg, logger
from src.models.video_metadata import VideoMetadata
from src.utils.video_handler import get_total_frames
from src.models.session import Session
from src.ui.utils.session_utils import delete_session

class ProcessSessionWorker(QThread):
    started = pyqtSignal()
    progress = pyqtSignal(str, object)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, session: Session, overwrite: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.session: Session = session
        self.overwrite: bool = overwrite
        self._is_canceled: bool = False

    def cancel(self):
        """Signal the thread to cancel its work."""
        self._is_canceled = True

    def update_state(self, message: str, progress: int | None = None):
        if progress:
            self.progress.emit(message, progress)
        else:
            self.progress.emit(message, None)

    def run(self):
        process = None
        try:
            # Check that the session doesn't already exist, if it does overwrite it.
            self.update_state("Checking session validity")
            if self.session.directory.exists():
                if self.overwrite:
                    delete_session(self.session)
                else:
                    raise FileExistsError(f"Session '{self.session.title}' already exists in the sessions directory.")

            # Create the session directory
            self.update_state("Creating session directory")
            self.session.directory.mkdir(parents=True, exist_ok=False)

            # Get the path to the ffmpeg executable.
            ffmpeg_path = ffmpeg.get_ffmpeg_exe()

            # Build the FFmpeg command.
            command = [
                ffmpeg_path,
                "-y",
                "-i", str(self.session.original_video_path),
                "-vsync", "cfr",
                "-r", str(cfg.video.fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-an",
                str(self.session.files.raw_video)
            ]

            # Retrieve the total frame count for progress calculation.
            total_frames = get_total_frames(self.session.original_video_path)

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
                if self._is_canceled:
                    process.kill()
                    process.wait()
                    if self.session.files.raw_video.exists():
                        self.session.files.raw_video.unlink()
                    self.canceled.emit()
                    return

                if "frame=" in line:
                    match = frame_regex.search(line)
                    if match:
                        current_frame = int(match.group(1))
                        progress_percent = int((current_frame / total_frames) * 100) if total_frames > 0 else 0
                        self.update_state("Cloning CFR video to session", progress_percent)

            process.wait()
            if process.returncode != 0:
                error_text = process.stderr.read()
                raise RuntimeError(f"FFmpeg error: {error_text}")

            process = None

            self.session.video_metadata = VideoMetadata.from_file(self.session.files.raw_video)

            self.update_state("Saving session config")

            with open(self.session.files.session_config, "w") as f:
                f.write(self.session.model_dump_json(indent=4))

            if self._is_canceled:
                self.session.video_metadata = None
                delete_session(self.session)
                self.canceled.emit()
                return

            self.update_state("Session setup complete")
            self.finished.emit()

        except Exception as e:
            if process is not None:
                process.kill()
                process.wait()

            delete_session(self.session)
            error_msg = f"Error processing video: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
