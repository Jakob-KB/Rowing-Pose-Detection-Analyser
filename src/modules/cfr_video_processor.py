from pathlib import Path
import imageio_ffmpeg as ffmpeg
import subprocess

from src.config import cfg, logger
from src.models.video_metadata import VideoMetadata
from src.utils.status_callback import status_callback
from src.utils.exceptions import ProcessCancelled
from src.utils.video_handler import get_total_frames


class ProcessCFRVideo:
    cancellation_message = "Cancelled."
    success_message = "Success."

    def __init__(self):
        self._is_cancelled = False

    def run(self, input_video_path: Path, output_video_path: Path, status=status_callback) -> VideoMetadata:
        self._is_cancelled = False

        process = None

        try:
            self._update_status(status,"Validating inputs to clone CFR video.")

            command = self._build_ffmpeg_command(input_video_path, output_video_path)
            total_frames = get_total_frames(input_video_path)

            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
            )

            frame_count = 0
            while True:
                if self._is_cancelled:
                    raise ProcessCancelled(self.cancellation_message)

                output_line = process.stdout.readline()
                if output_line == "" and process.poll() is not None:
                    break

                if output_line:
                    line = output_line.strip()
                    if line.startswith("frame="):
                        frame_count = self._parse_frame_count(line)
                        progress_value = (frame_count / total_frames * 100) if total_frames > 0 else 0
                        self._update_status(
                            status,
                            message="Cloning CFR video",
                            progress_value=progress_value
                        )

            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {stderr}")

            self._update_status(status, message=self.success_message)

            if self._is_cancelled:
                raise ProcessCancelled(self.cancellation_message)

            return VideoMetadata.from_file(output_video_path)

        except ProcessCancelled as e:
            self._handle_unexpected_exit(output_video_path, process)
            raise ProcessCancelled(e)
        except RuntimeError as e:
            self._handle_unexpected_exit(output_video_path, process)
            raise RuntimeError(e)
        except Exception as e:
            raise Exception(e)

    def cancel(self):
        self._is_cancelled = True

    @staticmethod
    def _build_ffmpeg_command(input_video: Path, output_video: Path) -> list:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        return [
            ffmpeg_path,
            "-y",
            "-i", str(input_video),
            "-loglevel", "quiet",
            "-progress", "pipe:1",  # Enables progress reporting via stdout
            "-vsync", "cfr",
            "-r", str(cfg.video.fps),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-an",
            str(output_video)
        ]

    @staticmethod
    def _parse_frame_count(line: str) -> int:
        try:
            return int(line.split('=')[1].strip())
        except (IndexError, ValueError):
            return 0

    @staticmethod
    def _update_status(status_callback_function, message: str, progress_value: float = None):
        if status_callback_function:
            status_callback_function(message=message, progress_value=progress_value)

    @staticmethod
    def _handle_unexpected_exit(output_video_path: Path, process: subprocess.Popen = None):
        if process is not None:
            process.terminate()
            process.wait()
        if output_video_path.exists():
            output_video_path.unlink()
