import yaml
from src.session import Session
from src.landmark_dataclasses import LandmarkData
from src.config import logger


def save_landmark_data_to_session(session: Session, landmark_data: LandmarkData) -> None:
    data_dict = landmark_data.to_dict()

    try:
        with open(session.landmark_data_path, "w") as f:
            yaml.safe_dump(data_dict, f, default_flow_style=False)
        logger.info(f"Landmark data saved to {session.landmark_data_path}")
    except Exception as e:
        logger.error(f"Error saving landmark data: {e}")
        raise Exception()

def load_landmark_data_from_session(session: Session) -> LandmarkData:
    if not session.landmark_data_path.exists():
        raise FileNotFoundError(f"Landmark file not found at {session.landmark_data_path}")

    try:
        with open(session.landmark_data_path, "r") as f:
            data_dict = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading landmark data: {e}")
        raise

    # Convert the dict into a LandmarkData object
    landmark_data = LandmarkData.from_dict(data_dict)
    logger.info(f"Landmark data loaded from {session.landmark_data_path}")
    return landmark_data