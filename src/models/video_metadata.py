# src/models/mediapipe_preferences.py

from pathlib import Path
from typing import Tuple

import cv2
from pydantic import BaseModel, conint, confloat


class VideoMetadata(BaseModel):
    fps: conint(ge=0)
    total_frames: conint(ge=0)
    height: conint(ge=0)
    width: conint(ge=0)

    @classmethod
    def from_file(cls, file_path: Path) -> "VideoMetadata":
        video = cv2.VideoCapture(str(file_path))
        if not video.isOpened():
            raise ValueError(f"Cannot open video file: {file_path}")

        fps = int(video.get(cv2.CAP_PROP_FPS))
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))

        video.release()

        if fps <= 0:
            raise ValueError(f"Invalid FPS detected ({fps}) in video: {file_path}")

        return cls(
            fps=fps,
            total_frames=total_frames,
            height=height,
            width=width
        )

    @classmethod
    def from_dict(cls, metadata_dict: dict) -> "VideoMetadata":
        return cls(**metadata_dict)

    def get_dimensions(self) -> Tuple[int, int]:
        return self.width, self.height
