# src/modules/session_manager.py

import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg as ffmpeg
import yaml
import re

from src.config import cfg, logger
from src.models.landmark_data import LandmarkData
from src.models.session import Session
from src.models.video_metadata import VideoMetadata
from src.utils.file_handler import check_session_file_exists
from src.utils.video_handler import get_total_frames
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.annotate_video import AnnotateVideo


class SessionManager:
    active_session: Session = None

    def set_active_session(self, session: Session) -> None:
        self.active_session = session

    @staticmethod
    def create_session(
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
    def process_session(session: Session, progress_callback=None) -> None:
        processor: ProcessLandmarks = ProcessLandmarks()
        landmark_data = processor.run(
            raw_video_path=session.files.raw_video,
            mediapipe_preferences=session.mediapipe_preferences,
            video_metadata=session.video_metadata,
            progress_callback=progress_callback
        )
        SessionManager.save_landmarks_to_session(session, landmark_data)

        # Annotate landmarks and skeleton in a new saved video_metadata
        annotator: AnnotateVideo = AnnotateVideo()
        annotator.run(
            raw_video_path=session.files.raw_video,
            annotated_video_path=session.files.annotated_video,
            video_metadata=session.video_metadata,
            landmark_data=landmark_data,
            annotation_preferences=session.annotation_preferences,
            progress_callback=progress_callback
        )

    @staticmethod
    def load_session(session_dir: Path) -> Session:
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
    def delete_session(session: Session) -> None:
        expected_session_files = session.files.expected_files()
        all_session_files = [file.name for file in session.session_dir.iterdir()]

        for file in all_session_files:
            if file not in expected_session_files:
                raise FileExistsError(f"Foreign file found in session directory, session will have to be deleted"
                                        f"manually: {file}")

        shutil.rmtree(session.session_dir)
        logger.info(f"Session '{session.title}' has been deleted from your session directory at {session.session_dir}")

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


def main():
    from src.config import DATA_DIR
    from src.utils.progress_callback import progress_callback

    sample_session_title = "sample_session"
    sample_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

    session_manager = SessionManager()

    sample_session = session_manager.create_session(
        session_title=sample_session_title,
        original_video_path=sample_video_path,
        overwrite=True,
        progress_callback=progress_callback
    )

    session_manager.process_session(
        session=sample_session,
        progress_callback=progress_callback
    )

    input(f"Press any key to delete '{sample_session_title}'...")

    session_manager.delete_session(sample_session)

if __name__ == "__main__":
    main()
