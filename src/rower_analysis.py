from pathlib import Path
import json
from datetime import datetime
import shutil
import os

from src.config import ANALYSES_DIR, logger
from utils.video_handler import validate_input_video

class RowerAnalysis:
    def __init__(self, unique_title: str, original_video_path: Path, overwrite: bool = False) -> None:
        # Analysis identifiers and root path
        self.title = unique_title
        self.analysis_path: Path = ANALYSES_DIR / self.title

        # Video paths
        self.original_video_path = original_video_path
        self.raw_video: Path = self.analysis_path / f"raw.mp4"
        self.annotated_video: Path = self.analysis_path / f"annotated.mp4"

        # Data paths
        self.landmark_data: Path = self.analysis_path / f"landmarks.yaml"
        self.metrics_data: Path = self.analysis_path / f"metrics.json"
        self.config_path: Path = self.analysis_path / "config.json"

        # Data objects
        self.config = {}

        # Init methods
        self._setup_analysis_directory(overwrite)
        self._init_config()

    def _init_config(self) -> None:

        # Create a new analysis config and save it to the analysis directory
        self.config = {
            "title": self.title,
            "creation_date": datetime.now().isoformat(),
            "paths": {
                "original_video_path": str(self.original_video_path.resolve()),
                "raw_video_path": str(self.raw_video.resolve()),
                "annotated_video_path": str(self.annotated_video.resolve()),
                "landmark_data_path": str(self.landmark_data.resolve()),
                "metrics_data_path": str(self.metrics_data.resolve())
            },
            "mediapipe_cfg": {
                "model_complexity": 1,
                "smooth_landmarks": True,
                "min_detection_confidence": 0.5,
                "min_tracking_confidence": 0.5
            }
        }
        self.save_config()

    def _setup_analysis_directory(self, overwrite: bool) -> None:
        # If the analysis directory and its config already exist, raise an error unless overwrite is True
        if self.analysis_path.exists() and (self.analysis_path / "config.json").exists():
            if not overwrite:
                raise FileExistsError(f"Analysis '{self.title}' already exists at {self.analysis_path}. "
                                      f"Load or overwrite the existing analysis instead.")
            else:
                try:
                    shutil.rmtree(self.analysis_path)
                    logger.info(f"Overwriting existing analysis at {self.analysis_path}")
                except Exception as e:
                    logger.error(f"Failed to remove existing analysis directory {self.analysis_path}: {e}")
                    raise
        try:
            self.analysis_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create analysis directory {self.analysis_path}: {e}")
            raise

        # Check if a raw video already exists in the analysis directory
        if self.raw_video.exists():
            if overwrite is False:
                raise FileExistsError("A raw video file already exists in the analysis directory. Either overwrite,"
                                  "delete or load the analysis instead.")
            elif overwrite is True:
                os.remove(self.raw_video)
                logger.info(f"Overwriting existing analysis at {self.analysis_path}")

        # Validate and clone raw video to analysis folder
        try:
            if validate_input_video(self.original_video_path):
                logger.info("Input video successfully validated.")

                # Check rower is facing right on the erg, if not mirror the video such that this is the case
                # if rower_facing_right(self.original_video_path) is False:
                    # Mirror the video before and clone the mirrored version as the raw video

                # Copy video to the analysis folder
                shutil.copy2(self.original_video_path, self.raw_video)
                logger.info(f"Raw video copied to {self.raw_video}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise

    def save_config(self) -> None:
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise

    @classmethod
    def load_existing_analysis(cls, analysis_folder: Path):
        # Locate and validate the config file from selected analysis dir
        config_path = analysis_folder / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"No config file found in {analysis_folder}")

        # Attempt to load the selected config file
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise

        # Attempt to create analysis instance based on the existing analysis config
        try:
            # Create analysis instance without calling __init__
            instance = cls.__new__(cls)

            # analysis identifiers and root path
            instance.title = config.get("title")
            if instance.title is None:
                raise ValueError("Config missing 'title'")
            instance.analysis_path = analysis_folder

            # Video paths
            instance.original_video_path = Path(config.get("original_video_path", ""))
            instance.raw_video = analysis_folder / f"raw.mp4"
            instance.annotated_video = analysis_folder / f"annotated.mp4"

            # Data paths
            instance.landmark_data = analysis_folder / f"landmarks.yaml"
            instance.metrics_data = analysis_folder / f"metrics.json"
            instance.config_path = config_path

            # Data objects
            instance.config = config
        except Exception as e:
            logger.error(f"Error initializing RowerAnalysis from {analysis_folder}: {e}")
            raise

        # Instance successfully loaded from the existing analysis
        logger.info(f"Loaded analysis from {analysis_folder}")
        return instance

# Example usage:
if __name__ == "__main__":
    from src.config import DATA_DIR

    title = "athlete_1"
    original_video = DATA_DIR / "videos" / f"{title}.mp4"

    # Try to create a new analysis with overwrite option (set to False by default)
    new_analysis = RowerAnalysis(title, original_video, overwrite=True)
    print("New analysis config:", new_analysis.config)

    load_existing_analysis = False

    if load_existing_analysis:
        # Load an existing analysis
        existing_analysis = ANALYSES_DIR / title
        loaded_analysis = RowerAnalysis.load_existing_analysis(existing_analysis)
        print("Loaded analysis config:", loaded_analysis.config)
