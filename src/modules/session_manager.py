# src/modules/session_manager.py

import shutil
from src.models.session import Session
from src.models.video_metadata import VideoMetadata

from pathlib import Path
import imageio_ffmpeg as ffmpeg
import re

import subprocess
from src.config import cfg, logger
from src.utils.exceptions import CancellationException
from src.utils.video_handler import get_total_frames
from src.models.cancelable_process import CancelableProcess

class SessionManager:
    @staticmethod
    def create_session(session_title: str, original_video_path: Path, overwrite: bool = False) -> Session:
        return Session.create(
            session_title=session_title,
            original_video_path=original_video_path,
            overwrite=overwrite,
        )

    @staticmethod
    def load_session(session_directory: Path, progress_callback=None) -> Session:
        """
        Loads a session configuration from a JSON file in the given session directory.
        """
        config_file = session_directory / cfg.session.files.session_config

        if progress_callback:
            progress_callback("Loading session", 0)

        if not config_file.exists():
            raise FileNotFoundError("Unable to find config file for the selected session.")

        try:
            with open(config_file, "r") as f:
                data = f.read()
            session = Session.model_validate_json(data)
            session.video_metadata = VideoMetadata.from_dict(session.video_metadata)
            logger.info(f"Session loaded from {config_file}.")

            if progress_callback:
                progress_callback("Loading session", 100)

            return session
        except Exception as e:
            logger.error(f"Error loading session configuration: {e}")
            raise

    @staticmethod
    def delete_session(session: Session) -> None:
        expected_session_files = session.files.expected_files()
        all_session_files = [file.name for file in session.directory.iterdir()]

        for file in all_session_files:
            if file not in expected_session_files:
                raise FileExistsError(
                    f"Foreign file found in session directory, session will have to be deleted manually: {file}"
                )

        shutil.rmtree(session.directory)
        logger.info(f"Session '{session.title}' has been deleted from {session.directory}")

class SessionSetup(CancelableProcess):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def run(self) -> None:
        """
        Sets up the session directory, clones the original video with CFR at the configured fps,
        and saves the session configuration. Cancellation is checked throughout the process.
        """
        # Handle existing session directory.
        if self.session.directory.exists():
            if not self.session.overwrite:
                logger.error("A session directory with this name already exists.")
                raise FileExistsError("A session directory with this name already exists.")
            else:
                shutil.rmtree(self.session.directory)
                logger.info(f"Existing session directory {self.session.directory} removed (overwrite enabled).")

        self.session.directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Session directory created at {self.session.directory}.")

        input_video_path = self.session.original_video_path
        output_video_path = self.session.files.raw_video

        # Clone the original video to the session directory with CFR at the target fps.
        total_frames = get_total_frames(input_video_path)
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg_path,
            "-y" if self.session.overwrite else "-n",
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
            # Check for cancellation on each line.
            if self.is_cancelled():
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
                        self.report_progress("Setting up session", progress)
                    except ValueError:
                        pass

        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {process.stderr.read()}")

        logger.info(f"Raw video processed and cloned with CFR to {output_video_path}")

        # Configure metadata for the session video.
        self.session.video_metadata = VideoMetadata.from_file(self.session.files.raw_video)

        # Save session configuration.
        try:
            with open(self.session.files.session_config, "w") as f:
                f.write(self.session.model_dump_json(indent=4))
            logger.info(f"Session configuration saved to {self.session.files.session_config}.")
        except Exception as e:
            raise FileNotFoundError(f"Error saving session configuration: {e}")