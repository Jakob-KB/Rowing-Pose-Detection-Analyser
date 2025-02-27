# src/sessions.py
import shutil
from src.session_config_manager import *
from src.config import *
import yaml
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
            shutil.copy2(temp_video_path, self.raw_video_path)
            logger.info(f"Raw video copied to {self.raw_video_path}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise Exception()

        # Delete the temp video_metadata now that raw video_metadata is saved to the session directory
        # os.remove(temp_video_path

    # Handle landmark data
    def save_landmark_data_to_session(self, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()

        try:
            with open(self.landmark_data_path, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {self.landmark_data_path}")
        except Exception as e:
            logger.error(f"Error saving landmark data: {e}")
            raise Exception()

    def load_landmark_data_from_session(self) -> LandmarkData:
        if not self.landmark_data_path.exists():
            raise FileNotFoundError(f"Landmark file not found at {self.landmark_data_path}")

        try:
            with open(self.landmark_data_path, "r") as f:
                data_dict = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading landmark data: {e}")
            raise

        # Convert the dict into a LandmarkData object
        landmark_data = LandmarkData.from_dict(data_dict)
        logger.info(f"Landmark data loaded from {self.landmark_data_path}")
        return landmark_data

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