# /src/models/session.py

from pydantic import BaseModel, Field
from pathlib import Path

from src.utils.misc import new_id, now_s
from src.config import get_api_config

cfg = get_api_config()

storage_dir = cfg.STORAGE_DIR

class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    status: str
    notes: str = ""
    created_at: int = Field(default_factory=now_s)
    updated_at: int = Field(default_factory=now_s)

    @property
    def processed_video_path(self) -> Path:
        return storage_dir / "appdata" / "videos" / f"{self.id}.mp4"

    @property
    def processed_video_uri(self) -> str:
        return f"/appdata/videos/{self.id}.mp4"

    @property
    def cover_image_path(self) -> Path:
        return storage_dir / "appdata" / "images" / f"{self.id}.png"

    @property
    def cover_image_uri(self) -> str:
        return f"/appdata/images/{self.id}.png"

    @property
    def evaluation_path(self):
        return storage_dir / "appdata" / "evaluations" / f"{self.id}.csv"

    @property
    def evaluation_uri(self):
        return f"/appdata/evaluations/{self.id}.csv"
