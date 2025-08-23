# /src/models/evaluation.py

from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

from src.utils.misc import new_id, now_s

class Evaluation(BaseModel):
    id: str = Field(default_factory=new_id)
    session_id: str
    video_id: str
    path: Path
    uri: Optional[str] = None
    mime_type: str
    avg_spm: Optional[float] = None
    created_at: int = Field(default_factory=now_s)
