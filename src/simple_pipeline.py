from src.config import DATA_DIR
from src.modules.video_annotator import VideoAnnotator
from src.modules.cfr_video_processor import ProcessCFRVideo
from src.modules.landmark_processor import LandmarkProcessor
from src.modules.session_manager import SessionManager


def main():
    session_title = "test_session"
    original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

    session_manager = SessionManager()
    clone_cfr_video = ProcessCFRVideo()

    landmark_processor = LandmarkProcessor()
    annotator = VideoAnnotator()

    session = session_manager.create_session(
        session_title=session_title,
        original_video_path=original_video_path,
        overwrite=True
    )

    clone_cfr_video.run(
        input_video_path=original_video_path,
        output_video_path=session.files.raw_video
    )

    session_manager.update_session(session)
    session_manager.save_session(session)

    landmark_data = landmark_processor.run(
        raw_video_path=session.files.raw_video,
        video_metadata=session.video_metadata

    )
    landmark_processor.save_landmark_data_to_file(
        landmark_data=landmark_data,
        file_path=session.files.landmark_data
    )

    annotator.run(
        raw_video_path=session.files.raw_video,
        annotated_video_path=session.files.annotated_video,
        video_metadata=session.video_metadata,
        landmark_data=landmark_data,
    )

if __name__ == "__main__":
    main()
