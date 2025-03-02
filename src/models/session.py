# src/models/session.py

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.config import SESSIONS_DIR, cfg
from src.models.annotation_preferences import AnnotationPreferences
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session_files import SessionFiles
# from src.models.video_metadata import VideoMetadata


class Session(BaseModel):
    title: str
    original_video_path: Path
    overwrite: bool
    session_dir: Path

    files: SessionFiles

    video_metadata: Any
    mediapipe_preferences: MediapipePreferences
    annotation_preferences: AnnotationPreferences

    @classmethod
    def create(
        cls,
        session_title: str,
        original_video_path: Path,
        overwrite: bool
    ) -> "Session":

        session_dir = SESSIONS_DIR / session_title

        files = SessionFiles(
            session_config=session_dir / cfg.session.files.session_config,
            raw_video=session_dir / cfg.session.files.raw_video,
            landmark_data=session_dir / cfg.session.files.landmark_data,
            analysis_data=session_dir / cfg.session.files.analysis_data,
            annotated_video=session_dir / cfg.session.files.annotated_video,
        )

        video_metadata = None

        annotation_preferences = AnnotationPreferences(
            bone_colour=cfg.session.annotation_preferences.bone_colour,
            bone_thickness=cfg.session.annotation_preferences.bone_thickness,
            landmark_colour=cfg.session.annotation_preferences.landmark_colour,
            landmark_radius=cfg.session.annotation_preferences.landmark_radius,
            reference_line_colour=cfg.session.annotation_preferences.reference_line_colour,
            reference_line_length=cfg.session.annotation_preferences.reference_line_length,
            reference_line_thickness=cfg.session.annotation_preferences.reference_line_thickness,
            reference_line_dash_factor=cfg.session.annotation_preferences.reference_line_dash_factor,
            opacity=cfg.session.annotation_preferences.opacity,
        )

        mediapipe_preferences = MediapipePreferences(
            model_complexity=cfg.session.mediapipe_preferences.model_complexity,
            smooth_landmarks=cfg.session.mediapipe_preferences.smooth_landmarks,
            min_detection_confidence=cfg.session.mediapipe_preferences.min_detection_confidence,
            min_tracking_confidence=cfg.session.mediapipe_preferences.min_tracking_confidence,
        )

        return cls(
            title=session_title,
            original_video_path=original_video_path,
            overwrite=overwrite,
            session_dir=session_dir,
            files=files,
            video_metadata=video_metadata,
            annotation_preferences=annotation_preferences,
            mediapipe_preferences=mediapipe_preferences
        )
