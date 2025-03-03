# src/models/mediapipe_preferences.py

from pydantic import BaseModel

from typing import Any

from src.utils.tokens import CancellationToken


class OperationControls(BaseModel):
    overwrite: bool = False
    progress_callback: Any = None
    cancellation_token: CancellationToken | None = None

    class Config:
        arbitrary_types_allowed = True