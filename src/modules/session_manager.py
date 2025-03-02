# src/modules/session_manager.py

import shutil
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg as ffmpeg
import yaml
import re

from src.config import cfg, logger
from src.models.landmark_data import LandmarkData
from src.models.session import Session
from src.models.video_metadata import VideoMetadata
from src.utils.file_handler import check_session_file_exists


def get_total_frames(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total


class SessionManager:
    active_session: Session = None

    def set_active_session(self, session: Session) -> None:
        self.active_session = session

    @staticmethod
    def new_session(
            session_title: str,
            original_video_path: Path,
            overwrite: bool = False,
            progress_callback=None) -> Session:

        session = Session.create(session_title=session_title, original_video_path=original_video_path)

        # Handle existing session directory
        if session.session_dir.exists():
            if not overwrite:
                logger.error("A session directory with this name already exists.")
                raise FileExistsError("A session directory with this name already exists.")
            else:
                shutil.rmtree(session.session_dir)
                logger.info(f"Existing session directory {session.session_dir} removed due to overwrite=True.")

        session.session_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Session directory created at {session.session_dir}.")

        # Clone the original video to session directory with CFR at 30fps
        try:
            total_frames = get_total_frames(original_video_path)

            ffmpeg_path = ffmpeg.get_ffmpeg_exe()
            command = [
                ffmpeg_path,
                "-y" if overwrite else "-n",
                "-i", str(original_video_path),
                "-vsync", "cfr",
                "-r", str(cfg.video.fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-an",
                str(session.files.raw_video)
            ]

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

            frame_regex = re.compile(r"frame=\s*(\d+)")

            # Read ffmpeg output live
            for line in iter(process.stderr.readline, ""):
                if "frame=" in line:
                    match = frame_regex.search(line)
                    if match:
                        try:
                            processed_frames = int(match.group(1))
                            progress = (processed_frames / total_frames) * 100
                            if progress_callback:
                                progress_callback("Setting up session", progress)
                        except ValueError:
                            pass

            process.wait()
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {process.stderr.read()}")

            logger.info(f"Raw video processed and cloned with CFR to {session.files.raw_video}")

        except Exception as e:
            logger.error(f"Error while processing raw video: {e}")
            raise

        # Configure metadata for any video associated with the session
        session.video_metadata = VideoMetadata.from_file(session.files.raw_video)

        # Save session configuration
        try:
            with open(session.files.session_config, "w") as f:
                f.write(session.model_dump_json(indent=4))
            logger.info(f"Session configuration saved to {session.files.session_config}.")
        except Exception as e:
            raise FileNotFoundError(f"Error saving session configuration: {e}")

        return session

    @staticmethod
    def load_existing_session(session_dir: Path) -> Session:
        """
        Loads a session configuration from a JSON file in the given session directory.
        """
        config_file = session_dir / cfg.session.files.session_config

        valid, msg = check_session_file_exists(config_file, "config file", session_dir.name)
        if not valid:
            raise FileNotFoundError(msg)

        try:
            with open(config_file, "r") as f:
                data = f.read()
            session = Session.model_validate_json(data)
            logger.info(f"Session loaded from {config_file}.")
            return session
        except Exception as e:
            logger.error(f"Error loading session configuration: {e}")
            raise

    @staticmethod
    def save_landmarks_to_session(session: Session, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()

        try:
            with open(session.files.landmark_data, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {session.files.landmark_data}")
        except Exception as e:
            logger.error(f"Error saving landmark data: {e}")
            raise Exception()

    @staticmethod
    def load_landmarks_from_session(session: Session) -> LandmarkData:
        if not session.files.landmark_data.exists():
            raise FileNotFoundError(f"Landmark file not found at {session.files.landmark_data}")

        with open(session.files.landmark_data, "r") as f:
            data_dict = yaml.safe_load(f)

        landmark_data = LandmarkData.from_dict(data_dict)
        logger.info(f"Landmark data loaded from {session.files.landmark_data}")
        return landmark_data
