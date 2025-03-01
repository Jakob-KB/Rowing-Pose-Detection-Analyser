# src/models/mediapipe_preferences.py
from pydantic import BaseModel

class MediapipePreferences(BaseModel):
    model_complexity: int
    smooth_landmarks: bool
    min_detection_confidence: float
    min_tracking_confidence: float