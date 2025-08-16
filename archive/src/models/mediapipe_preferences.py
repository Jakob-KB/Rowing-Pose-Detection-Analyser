# src/models/mediapipe_preferences.py

from pydantic import BaseModel, conint, confloat
from src.config import cfg


class MediapipePreferences(BaseModel):
    model_complexity: conint(ge=0, le=2) = cfg.session.mediapipe_preferences.model_complexity
    smooth_landmarks: bool = cfg.session.mediapipe_preferences.smooth_landmarks
    min_detection_confidence: confloat(ge=0, le=1) = cfg.session.mediapipe_preferences.min_detection_confidence
    min_tracking_confidence: confloat(ge=0, le=1) = cfg.session.mediapipe_preferences.min_tracking_confidence
