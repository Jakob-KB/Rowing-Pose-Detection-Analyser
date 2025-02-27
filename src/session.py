# src/sessions.py
import shutil
from src.io.io_session_config import *
from src.config import *
import imageio_ffmpeg as ffmpeg
import yaml
import subprocess
from src.landmark_dataclasses import LandmarkData

class Session:
    def __init__(self, session_title: str, temp_video_path: Path, overwrite: bool = False) -> None:
        # Session identifiers and root path
        self.title = session_title
        self.overwrite = overwrite

        session_dir = Path(SESSIONS_DIR / session_title)

        # Clear the session directory if it already exists and overwrite is true
        if session_dir.exists():
            if self.overwrite is False:
                logger.error("A session directory with this name already exists.")
                raise FileExistsError()
            else:
                shutil.rmtree(session_dir)

        self.session_dir = session_dir
        self.raw_video_path = session_dir / cfg.session_file_names.raw_video
        self.annotated_video_path = session_dir / cfg.session_file_names.annotated_video
        self.landmark_data_path = session_dir / cfg.session_file_names.landmark_data
        self.analysis_data_path = session_dir / cfg.session_file_names.analysis_data
        self.session_config_path = session_dir / cfg.session_file_names.session_config

        # Session config dict
        self.config: Dict = {}

        # Init methods
        self._setup_session_directory(temp_video_path)
        init_session_config(self)

    def _setup_session_directory(self, temp_video_path: Path) -> None:
        # Attempt to create a session directory
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {self.session_dir}: {e}")
            raise Exception()

        # Attempt to clone the video_metadata to the session directory
        try:
            # Get ffmpeg binary path
            ffmpeg_path = ffmpeg.get_ffmpeg_exe()

            # Ffmpeg command to enforce CFR at 30 FPS
            command = [
                ffmpeg_path, "-y" if self.overwrite else "-n",  # -y = overwrite, -n = skip if exists
                "-i", str(temp_video_path),  # Input video
                "-vsync", "cfr",  # Force constant frame rate
                "-r", str(cfg.video.fps),  # Set FPS
                "-c:v", "libx264",  # H.264 encoding
                "-preset", "fast",  # Speed vs quality tradeoff
                "-crf", "18",  # High-quality compression
                "-an",  # Remove any existing audio component
                str(self.raw_video_path)  # Output file
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Raw video copied to {self.raw_video_path}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise Exception()

        # Delete the temp video_metadata now that raw video_metadata is saved to the session directory
        # os.remove(temp_video_path

    # Loading Existing Session
    @classmethod
    def load_existing_session(cls, session_dir: Path) -> "Session":
        config_file_path = session_dir / "session_config.json"
        if not config_file_path.exists():
            raise FileNotFoundError(f"No config file found at {config_file_path}")

        try:
            with open(config_file_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_file_path}: {e}")
            raise

        # Create an instance without calling __init__
        instance = cls.__new__(cls)
        apply_config(instance, config)
        return instance

# Example usage:
if __name__ == "__main__":
    from src.config import DATA_DIR

    title = "athlete_1"
    original_video = DATA_DIR / "videos" / f"{title}.mp4"

    # Create a new session with overwrite option (set to False by default)
    new_session = Session(title, original_video, overwrite=True)
    print("New session config:", new_session.config)

    load_existing_session = False

    if load_existing_session:
        # Load an existing session
        existing_session = SESSIONS_DIR / title
        loaded_session = Session.load_existing_session(existing_session)
        print("Loaded session config:", loaded_session.config)