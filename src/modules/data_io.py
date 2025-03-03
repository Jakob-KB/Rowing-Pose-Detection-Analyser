
from pathlib import Path
from src.models.landmark_data import LandmarkData
import yaml
from src.config import logger

class DataIO:
    @staticmethod
    def load_landmark_data_from_file(file_path: Path) -> LandmarkData:
        if not file_path.exists():
            raise FileNotFoundError(f"Landmark file not found at {file_path}")

        with open(file_path, "r") as f:
            data_dict = yaml.safe_load(f)

        landmark_data = LandmarkData.from_dict(data_dict)
        logger.info(f"Landmark data loaded from {file_path}")
        return landmark_data

    @staticmethod
    def save_landmark_data_to_file(file_path: Path, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()

        try:
            with open(file_path, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {file_path}")
        except Exception as e:
            raise FileNotFoundError(f"Error saving landmark data: {e}")