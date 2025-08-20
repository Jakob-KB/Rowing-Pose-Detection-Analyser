# src/services/video.py
from __future__ import annotations

from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Dict

from src.config import get_api_config
from src.integrations import (
    load_video_file,
    resize_video,
    cfr_video,
    save_video_file,
    save_cover_image,
    get_video_metadata_from_file,
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

        self._ensure_storage_dirs()

    # Public API
    def create_session(self, name: str, video_path: Path) -> Session:
        self._validate_file_path(video_path)

        if self.db.session_name_exists(name):
            raise ValueError("Session name already exists")

        session = Session(
            name=name,
            status="empty",
            notes=""
        )
        self.db.insert_session(session)

        raw_video = self._build_raw_video(
            session_id=session.id,
            video_path=video_path
        )
        self.db.insert_raw_video(raw_video)

        return session

    def process_session(self, session_id: str) -> Session:
        raw_video: RawVideo = self.db.get_raw_video(session_id)

        raw_video_path = Path(raw_video.path_local)

        self._validate_file_path(raw_video_path)

        with self._status_guard(session_id, on_start=SessionStatus.PROCESSING, on_error=SessionStatus.ERROR):
            processed_video_path = self._transcode_to_target(session_id, raw_video_path)

            processed = self._build_processed_video(session_id, processed_video_path)
            self.db.insert_processed_video(processed)

            cover = self._build_cover_image(session_id, processed_video_path)
            self.db.insert_cover_image(cover)

            evaluation = process_landmarks_pts_models(processed)
            self.db.insert_evaluation(evaluation)

            self._update_status(session_id, SessionStatus.DONE)

        # return fresh session object with updated status
        return self.db.get_session(session_id)

    # Internal helpers
    def _ensure_storage_dirs(self) -> None:
        """
        May want to remove this somewhere else (probably to some central application startup sequence.
        """
        (self.storage_dir / "appdata" / "videos").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "appdata" / "images").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "appdata" / "images").mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_file_path(path: Path) -> None:
        if not isinstance(path, Path):
            raise TypeError("video_path must be a pathlib.Path")
        if not path.exists():
            raise FileNotFoundError(f"Video file does not exist: {path}")

    def _session_filepaths(self, session_id: str) -> Dict[str, Path | str]:
        """
        Returns dict with session specific filepaths and URIs
        """
        processed_video_path: Path = self.storage_dir / "appdata" / "videos" / f"{session_id}.mp4"
        processed_video_uri: str = f"appdata/videos/{session_id}.mp4"

        cover_image_path: Path = self.storage_dir / "appdata" / "images" / f"{session_id}.png"
        cover_image_uri: str = f"appdata/images/{session_id}.png"

        evaluation_path: Path = self.storage_dir / "appdata" / "evaluations" / f"{session_id}.parquet"
        evaluation_uri: str = f"appdata/images/{session_id}.parquet"

        return {
            "processed_video_path": processed_video_path,
            "processed_video_uri": processed_video_uri,
            "cover_image_path": cover_image_path,
            "cover_image_uri": cover_image_uri,
            "evaluation_path": evaluation_path,
            "evaluation_uri": evaluation_uri
        }

    def _transcode_to_target(self, session_id: str, video_path: Path) -> Path:
        clip = load_video_file(video_path=video_path)
        clip_1080 = resize_video(clip, target_w=self.target_width, target_h=self.target_height)
        clip_cfr = cfr_video(clip_1080, target_fps=self.target_fps)

        session_files = self._session_filepaths(session_id)
        save_video_file(clip_cfr, out_path=session_files["processed_video_path"], fps=self.target_fps)
        return session_files["processed_video_path"]

    @staticmethod
    def _build_raw_video(session_id: str, video_path: Path) -> RawVideo:
        meta = get_video_metadata_from_file(video_path)
        return RawVideo(
            session_id=session_id,
            path_local=str(video_path),
            **meta,
        )

    def _build_processed_video(self, session_id: str, video_path: Path) -> ProcessedVideo:
        session_filepaths = self._session_filepaths(session_id)
        meta = get_video_metadata_from_file(video_path)
        return ProcessedVideo(
            session_id=session_id,
            path_local=str(video_path),
            uri=session_filepaths["processed_video_uri"],
            **meta,
        )

    def _build_cover_image(self, session_id: str, video_path: Path) -> CoverImage:
        session_filepaths = self._session_filepaths(session_id)

        clip = load_video_file(video_path=video_path)
        save_cover_image(clip, out_path=session_filepaths["cover_image_path"])

        meta = {
            "mime_type": "image/png",
            "width": 1920,
            "height": 1080
        }
        return CoverImage(
            session_id=session_id,
            path_local=session_filepaths["cover_image_path"],
            uri=session_filepaths["cover_image_uri"],
            **meta
        )

    def _update_status(self, session_id: str, status: SessionStatus) -> None:
        self.db.update_session_status(session_id, status.value)

    @contextmanager
    def _status_guard(self, session_id: str, on_start: SessionStatus, on_error: SessionStatus):
        self._update_status(session_id, on_start)
        try:
            yield
        except Exception:
            # Ensure DB reflects failure, then re-raise
            self._update_status(session_id, on_error)
            raise
