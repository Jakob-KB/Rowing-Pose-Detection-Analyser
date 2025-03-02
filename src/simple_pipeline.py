# src/simple_pipeline.py

from pathlib import Path
import sys

from src.config import DATA_DIR
from src.models.session import Session
from src.modules.session_manager import SessionManager
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.annotate_video import AnnotateVideo


def progress_callback(stage: str, progress: float) -> None:
    sys.stdout.write(f"\r{stage}: {progress:.2f}% completed")
    sys.stdout.flush()

    if progress >= 100:
        sys.stdout.write("\n")
        sys.stdout.flush()


def main() -> None:
    session_title: str = "athlete_1"
    input_video_path: Path = DATA_DIR / "videos" / "athlete_1.mp4"

    # Create a new session
    session_manager: SessionManager = SessionManager()
    session: Session = session_manager.new_session(session_title, input_video_path, overwrite=True,
                                                   progress_callback=progress_callback)

    # Process landmarks in the raw video_metadata and save them to session
    processor: ProcessLandmarks = ProcessLandmarks()
    landmark_data = processor.run(
        raw_video_path=session.files.raw_video,
        mediapipe_preferences=session.mediapipe_preferences,
        video_metadata=session.video_metadata,
        progress_callback=progress_callback
    )
    session_manager.save_landmarks_to_session(session, landmark_data)

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


if __name__ == "__main__":
    main()
