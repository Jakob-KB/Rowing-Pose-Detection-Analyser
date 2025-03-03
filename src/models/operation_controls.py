# src/models/mediapipe_preferences.py

from pydantic import BaseModel

from typing import Callable, Any

from src.utils.tokens import CancellationToken


class OperationControls(BaseModel):
    overwrite: bool
    progress_callback: Any
    cancellation_token: CancellationToken

    class Config:
        arbitrary_types_allowed = True