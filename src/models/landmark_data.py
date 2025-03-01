# src/landmark_dataclasses.py
from typing import Dict, List, Tuple
from pydantic import BaseModel
from src.config import logger, cfg

class Landmark(BaseModel):
    """
    Represents a single landmark with normalized coordinates (x, y) and visibility.
    """
    x: float
    y: float
    visibility: float
    frame: int
    name: str

    def get_screen_position(self) -> Tuple[int, int]:
        """
        Convert normalized coordinates to pixel positions based on video metadata dimensions.
        """
        return int(cfg.video.width * self.x), int(cfg.video.height * self.y)


class FrameLandmarks(BaseModel):
    """
    Encapsulates landmarks for a single frame.
    """
    frame: int
    landmarks: Dict[str, Landmark]

    @classmethod
    def from_dict(cls, frame_num: int, data: Dict[str, Dict[str, float]]) -> "FrameLandmarks":
        _landmarks = {
            name: Landmark(
                x=entry.get("x", 0.0),
                y=entry.get("y", 0.0),
                visibility=entry.get("visibility", 0.0),
                frame=frame_num,
                name=name
            )
            for name, entry in data.items()
        }
        return cls(frame=frame_num, landmarks=_landmarks)

    def get_landmark(self, landmark_name: str) -> Landmark:
        if landmark_name in self.landmarks:
            return self.landmarks[landmark_name]
        else:
            logger.error(f"Failed to get landmark '{landmark_name}' for the current frame")
            raise KeyError(f"Landmark '{landmark_name}' not found")

    def get_landmarks(self) -> List[Landmark]:
        return list(self.landmarks.values())


class LandmarkData(BaseModel):
    frames: Dict[int, FrameLandmarks]

    @classmethod
    def from_dict(cls, data: Dict[int, Dict[str, Dict[str, float]]]) -> "LandmarkData":
        frames = {
            frame_num: FrameLandmarks.from_dict(frame_num, frame_data)
            for frame_num, frame_data in data.items()
        }
        return cls(frames=frames)

    def to_dict(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        output = {}
        for frame_num, frame_landmarks in self.frames.items():
            landmarks_dict = {}
            for name, landmark_obj in frame_landmarks.landmarks.items():
                landmarks_dict[name] = {
                    "x": landmark_obj.x,
                    "y": landmark_obj.y,
                    "z": getattr(landmark_obj, "z", 0.0),  # If you store z as well
                    "visibility": landmark_obj.visibility
                }
            output[frame_num] = landmarks_dict
        return output

    def get_frame_landmarks(self, frame_num: int) -> FrameLandmarks:
        if frame_num in self.frames:
            return self.frames[frame_num]
        else:
            logger.error(f"Failed to get landmarks for frame {frame_num}")
            raise KeyError(f"Frame {frame_num} not found")
