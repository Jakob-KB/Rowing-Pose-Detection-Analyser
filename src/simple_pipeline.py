from src.config import DATA_DIR
from src.models.operation_controls import OperationControls
from src.modules.annotate_video import AnnotateVideo
from src.modules.data_io import DataIO
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.session_manager import SessionManager
from src.utils.progress_callback import progress_callback


def main():
    session_title = "athlete_1"
    original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

    session_manager = SessionManager()
    processor = ProcessLandmarks()
    annotator = AnnotateVideo()
    data_io = DataIO()

    operation_controls = OperationControls(
        overwrite=True,
        progress_callback=progress_callback,
        cancellation_token=None
    )

    session = session_manager.create_session(
        session_title=session_title,
        original_video_path=original_video_path
    )

    session_manager.setup_session_directory(
        session=session,
        operation_controls=operation_controls
    )

    landmark_data = processor.run(
        raw_video_path=session.files.raw_video,
        video_metadata=session.video_metadata,
        mediapipe_preferences=session.mediapipe_preferences,
        operation_controls=operation_controls
    )

    data_io.save_landmark_data_to_file(
        file_path=session.files.landmark_data,
        landmark_data=landmark_data,
    )

    annotator.run(
        raw_video_path=session.files.raw_video,
        annotated_video_path=session.files.annotated_video,
        landmark_data=landmark_data,
        video_metadata=session.video_metadata,
        annotation_preferences=session.annotation_preferences,
        operation_controls=operation_controls
    )


if __name__ == "__main__":
    main()
