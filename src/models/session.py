from pydantic import BaseModel
from pathlib import Path

class Session(BaseModel):
    id: str
    name: str
    original_video_filepath: Path
    processed_video_filepath: Path
    processed_video_fileurl: str
    cover_image_filepath: Path
    cover_image_fileurl: str
    status: str
    created_at: float
    updated_at: float
