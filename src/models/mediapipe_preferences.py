# src/models/mediapipe_preferences.py

from pydantic import BaseModel, conint, confloat


class MediapipePreferences(BaseModel):
    model_complexity: conint(ge=0, le=2)
    smooth_landmarks: bool
    min_detection_confidence: confloat(ge=0, le=1)
    min_tracking_confidence: confloat(ge=0, le=1)
