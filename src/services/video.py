# src/services/video.py
from __future__ import annotations

from pathlib import Path

from src.config import get_api_config
from src.services.database import DatabaseServices

cfg = get_api_config()

class VideoServices:
    def __init__(self, db: DatabaseServices) -> None:
        self.db = db
        self.target_width: int = cfg.VIDEO_WIDTH
        self.target_height: int = cfg.VIDEO_HEIGHT
        self.target_fps: float = cfg.VIDEO_FPS
        self.storage_dir: Path = cfg.STORAGE_DIR


    def process_video(self, session_id: str):
        pass
