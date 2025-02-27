# src/main.py
from session import Session

from config import DATA_DIR
from pathlib import Path
from video_processing import ProcessLandmarks, AnnotateVideo


def main() -> None:
    video_title: str = "athlete_1"
    input_video_path: Path = DATA_DIR / "videos" / "athlete_1.mp4"

    # Create a new session
    sample_session: Session = Session(video_title, input_video_path, overwrite=True)

    # Process landmarks in the raw video_metadata and save them to session
    pose_estimator: ProcessLandmarks = ProcessLandmarks(sample_session)
    landmark_data = pose_estimator.run()
    sample_session.save_landmark_data_to_session(landmark_data)

    # Annotate landmarks and skeleton in a new saved video_metadata
    annotator: AnnotateVideo = AnnotateVideo(sample_session)
    annotator.run()


if __name__ == "__main__":
    main()
