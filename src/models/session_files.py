# src/models/session_files.py

from pathlib import Path

from pydantic import BaseModel


class SessionFiles(BaseModel):
    session_config: Path
    raw_video: Path
    landmark_data: Path
    analysis_data: Path
    annotated_video: Path
