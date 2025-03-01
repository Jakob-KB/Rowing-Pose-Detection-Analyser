# src/models/session.py
from pydantic import BaseModel
from pathlib import Path
from src.config import SESSIONS_DIR, cfg
from src.models.annotation_preferences import AnnotationPreferences
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session_files import SessionFiles


class Session(BaseModel):
    """Session metadata, linked with annotation and processing preferences."""
    title: str
    original_video_path: Path
    session_dir: Path

    files: SessionFiles

    mediapipe_preferences: MediapipePreferences
    annotation_preferences: AnnotationPreferences

    @classmethod
    def create(
        cls,
        session_title: str,
        original_video_path: Path
    ) -> "Session":

        session_dir = SESSIONS_DIR / session_title

        files = SessionFiles(
            session_config=session_dir / cfg.session.files.session_config,
            raw_video=session_dir / cfg.session.files.raw_video,
            landmark_data=session_dir / cfg.session.files.landmark_data,
            analysis_data=session_dir / cfg.session.files.analysis_data,
            annotated_video=session_dir / cfg.session.files.annotated_video,
        )

        annotation_preferences = AnnotationPreferences(
            bone_colour=cfg.session.annotation_prefs.bone.colour,
            bone_thickness=cfg.session.annotation_prefs.bone.thickness,
            landmark_colour=cfg.session.annotation_prefs.landmark.colour,
            landmark_radius=cfg.session.annotation_prefs.landmark.radius,
            reference_line_colour=cfg.session.annotation_prefs.reference_line.colour,
            reference_line_length=cfg.session.annotation_prefs.reference_line.length,
            reference_line_thickness=cfg.session.annotation_prefs.reference_line.thickness,
            reference_line_dash_factor=cfg.session.annotation_prefs.reference_line.dash_factor,
            opacity=cfg.session.annotation_prefs.opacity,
        )

        mediapipe_preferences = MediapipePreferences(
            model_complexity=cfg.session.mediapipe_prefs.model_complexity,
            smooth_landmarks=cfg.session.mediapipe_prefs.smooth_landmarks,
            min_detection_confidence=cfg.session.mediapipe_prefs.min_detection_confidence,
            min_tracking_confidence=cfg.session.mediapipe_prefs.min_tracking_confidence,
        )

        return cls(
            title=session_title,
            original_video_path=original_video_path,
            session_dir=SESSIONS_DIR / session_title,
            files=files,
            annotation_preferences=annotation_preferences,
            mediapipe_preferences=mediapipe_preferences
        )

