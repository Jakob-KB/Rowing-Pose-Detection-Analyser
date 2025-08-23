# /src/models/session_view.py

from pydantic import BaseModel
from typing import Optional

from .processed_video import ProcessedVideo
from .evaluation import Evaluation
from .cover_image import CoverImage


class SessionView(BaseModel):
    id: str
    name: str
    status: str
    notes: str

    processed_video: Optional[ProcessedVideo] = None
    evaluation: Optional[Evaluation] = None
    cover_image: Optional[CoverImage] = None

    created_at: int
    updated_at: int
