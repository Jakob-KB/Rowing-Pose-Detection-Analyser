# src/services/video.py
from pathlib import Path
from src.config import get_api_config
from src.integrations import (
    load_video_file,
    resize_video,
    cfr_video,
    save_video_file,
    save_cover_image,
    get_video_metadata_from_file,
)
from src.models import (
    Session,
    RawVideo,
    ProcessedVideo,
    CoverImage,
    Evaluation
)
from src.utils.misc import validate_file_path
from src.integrations.mediapipe import process_landmarks_pts_models, save_landmarks_to_file

cfg = get_api_config()

class MediaServices:
    def __init__(self, session: Session, raw_video_path: Path) -> None:
        self.target_width: int = cfg.VIDEO_WIDTH
        self.target_height: int = cfg.VIDEO_HEIGHT
        self.target_fps: float = cfg.VIDEO_FPS
        self.storage_dir: Path = cfg.STORAGE_DIR

        self.session_id = session.id
        self.session = session

        self.raw_video_path: Path = raw_video_path

        self.processed_video_path: Path = session.processed_video_path
        self.processed_video_uri: str = session.processed_video_uri

        self.cover_image_path: Path = session.cover_image_path
        self.cover_image_uri: str = session.cover_image_uri

        self.evaluation_path: Path = session.evaluation_path
        self.evaluation_uri: str = session.evaluation_uri

        self._raw_clip = None
        self._processed_clip = None
        self._cover_image = None

        self._df = None


    def load_raw_video(self, input_video_path: Path):
        self._raw_clip = load_video_file(input_video_path)

    def process_video(self) -> ProcessedVideo:
        if not self._raw_clip:
            self.load_raw_video(self.raw_video_path)

        _clip = resize_video(
            self._raw_clip,
            target_w=self.target_width,
            target_h=self.target_height
        )
        self._processed_clip = cfr_video(
            _clip,
            target_fps=self.target_fps
        )

        save_video_file(
            self._processed_clip,
            fps=self.target_fps,
            output_path=self.processed_video_path
        )
        meta = get_video_metadata_from_file(self.processed_video_path)

        return ProcessedVideo(
            session_id=self.session_id,
            path=self.processed_video_path,
            uri=self.processed_video_uri,
            **meta
        )

    def evaluate_video(self, processed_video_id: str) -> Evaluation:
        if not self._processed_clip:
            self._processed_clip = load_video_file(self.processed_video_path)

        self._df = process_landmarks_pts_models(self.processed_video_path)
        save_landmarks_to_file(self._df, self.evaluation_path)

        return Evaluation(
            session_id=self.session_id,
            video_id=processed_video_id,
            path=self.evaluation_path,
            uri=self.evaluation_uri,
            mime_type="text/csv",
            avg_spm=24.0
        )

    def process_cover_image(self) -> CoverImage:
        if not self._processed_clip:
            self._processed_clip = load_video_file(self.processed_video_path)

        save_cover_image(
            self._processed_clip,
            output_path=self.cover_image_path
        )

        meta = {"mime_type": "image/png", "width": 1920, "height": 1080}
        return CoverImage(
            session_id=self.session_id,
            path=self.cover_image_path,
            uri=self.cover_image_uri,
            **meta
        )
