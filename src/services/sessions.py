# src/services/video.py
from __future__ import annotations

from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Dict

from src.config import get_api_config
from src.integrations import (
    load_video_file,
    save_cover_image,
    get_video_metadata_from_file
)
from src.integrations.mediapipe import process_landmarks_pts_models
from src.models import (
    Session,
    RawVideo,
    ProcessedVideo,
    CoverImage,
    Evaluation
)
from src.services.database import DatabaseServices
from .media import MediaServices
from src.utils.misc import validate_file_path

cfg = get_api_config()


class SessionStatus(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class SessionServices:
    def __init__(self, db: DatabaseServices) -> None:
        self.db = db
        self.target_width: int = cfg.VIDEO_WIDTH
        self.target_height: int = cfg.VIDEO_HEIGHT
        self.target_fps: float = cfg.VIDEO_FPS
        self.storage_dir: Path = cfg.STORAGE_DIR


    # Public API
    def create_session(self, name: str, video_path: Path) -> Session:
        validate_file_path(video_path)

        if self.db.session_name_exists(name):
            raise ValueError("Session name already exists")

        session = Session(
            name=name,
            status="new",
            notes=""
        )
        self.db.insert_session(session)

        meta = get_video_metadata_from_file(video_path)
        raw_video = RawVideo(
            session_id=session.id,
            path=video_path,
            **meta
        )
        self.db.insert_raw_video(raw_video)


        return session

    def process_session(self, session_id: str) -> Session:
        self.db.update_session_status(session_id, "processing")

        session = self.db.get_session(session_id)
        raw_video = self.db.get_raw_video(session_id)

        media_service = MediaServices(
            session=session,
            raw_video_path=raw_video.path
        )

        processed_video: ProcessedVideo = media_service.process_video()
        self.db.insert_processed_video(processed_video)

        evaluation: Evaluation = media_service.evaluate_video(processed_video.id)
        self.db.insert_evaluation(evaluation)

        cover_image: CoverImage = media_service.process_cover_image()
        self.db.insert_cover_image(cover_image)

        self.db.update_session_status(session_id, "error")

        # return fresh session object with updated status
        return self.db.get_session(session_id)

    @staticmethod
    def _build_raw_video(session_id: str, video_path):
        meta = get_video_metadata_from_file(video_path)
        return RawVideo(
            session_id=session_id,
            path=video_path,
            **meta
        )
