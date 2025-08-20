# /src/models/cover_image.py

from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

from src.utils.misc import new_id, now_s

class CoverImage(BaseModel):
    id: str = Field(default_factory=new_id)
    session_id: str
    path_local: Path
    uri: Optional[str] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: int = Field(default_factory=now_s)

    def get_path(self) -> Path:
        return Path(self.path_local)
