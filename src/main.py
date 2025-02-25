# src/main.py

from config import DATA_DIR
from pathlib import Path
from session import Session
from video_processing import PoseEstimator, AnnotateVideo

def main() -> None:
    video_title: str = "athlete_1"
    input_video_path: Path = DATA_DIR / "videos" / "athlete_1.mp4"

    # Create a new session
    sample_session: Session = Session(video_title, input_video_path, overwrite=True)

    # Process and detect landmarks in the raw video
    pose_estimator = PoseEstimator(sample_session, overwrite=True)
    pose_estimator.process_landmarks()

    # Annotate landmarks and skeleton in a new saved video
    annotator: AnnotateVideo = AnnotateVideo(sample_session, overwrite=True)
    annotator.annotate_video()



if __name__ == "__main__":
    main()
