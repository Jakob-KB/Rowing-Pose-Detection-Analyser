# src/models/annotation_preferences.py
from pydantic import BaseModel
from pathlib import Path

class SessionFiles(BaseModel):
    session_config: Path
    raw_video: Path
    landmark_data: Path
    analysis_data: Path
    annotated_video: Path
