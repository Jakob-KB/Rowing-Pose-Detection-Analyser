from src.config import DATA_DIR
from src.modules.annotate_video import AnnotateVideo
from src.modules.data_io import DataIO
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.session_manager import SessionManager, SessionSetup
from src.utils.progress_callback import progress_callback


def main():
    session_title = "athlete_1"
    original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

    session_manager = SessionManager()
    data_io = DataIO()

    # Create session
    session = session_manager.create_session(
        session_title=session_title,
        original_video_path=original_video_path
    )

    # Setup session
    session_setup = SessionSetup(session)
    session_setup.set_progress_callback(progress_callback)
    session_setup.run()

    # Process landmarks
    processor = ProcessLandmarks(
        raw_video_path=session.files.raw_video,
        video_metadata=session.video_metadata,
        mediapipe_preferences=session.mediapipe_preferences
    )
    processor.set_progress_callback(progress_callback)
    landmark_data = processor.run()

    # Save landmark data
    data_io.save_landmark_data_to_file(
        file_path=session.files.landmark_data,
        landmark_data=landmark_data
    )

    # Annotate video
    annotator = AnnotateVideo(
        raw_video_path=session.files.raw_video,
        annotated_video_path=session.files.annotated_video,
        landmark_data=landmark_data,
        video_metadata=session.video_metadata,
        annotation_preferences=session.annotation_preferences
    )
    annotator.set_progress_callback(progress_callback)
    annotator.run()


if __name__ == "__main__":
    main()
