# /src/models/session_view.py

from pydantic import BaseModel
from typing import Optional

from .cover_image import CoverImage
from .evaluation import Evaluation

class SessionView(BaseModel):
    id: str
    name: str
    status: str
    notes: str

    cover_image: Optional[CoverImage] = None
    evaluation: Optional[Evaluation] = None

    created_at: int
    updated_at: int
