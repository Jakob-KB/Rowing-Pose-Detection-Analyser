# src/models/session.py

from pathlib import Path

from pydantic import BaseModel

from src.models.annotation_preferences import AnnotationPreferences
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session_files import SessionFiles
from src.models.video_metadata import VideoMetadata


class Session(BaseModel):
    title: str
    original_video_path: Path
    directory: Path | str

    files: SessionFiles

    video_metadata: VideoMetadata | None

    mediapipe_preferences: MediapipePreferences
    annotation_preferences: AnnotationPreferences
