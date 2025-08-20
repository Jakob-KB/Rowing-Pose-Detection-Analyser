# /src/models/raw_video.py

from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

from src.utils.misc import new_id, now_s

class RawVideo(BaseModel):
    id: str = Field(default_factory=new_id)
    session_id: str
    path_local: str
    mime_type: Optional[str] = None
    duration_s: Optional[float] = None
    frame_count: Optional[int] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: int = Field(default_factory=now_s)

    def get_path_local(self) -> Path:
        return Path(self.path_local)
