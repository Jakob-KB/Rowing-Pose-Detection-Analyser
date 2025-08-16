# src/models/landmark_data.py

from typing import Dict, List, Tuple

from pydantic import BaseModel, conint


class Landmark(BaseModel):
    """
    Represents a single landmark with normalized coordinates (x, y) and visibility.
    """
    x: int
    y: int
    frame: conint(ge=0)
    name: str

    def get_position(self) -> Tuple[int, int]:
        return self.x, self.y


class FrameLandmarks(BaseModel):
    """
    Encapsulates landmarks for a single frame.
    """
    frame: conint(ge=0)
    landmarks: Dict[str, Landmark]

    @classmethod
    def from_dict(cls, frame_num: int, data: Dict[str, Dict[str, float]]) -> "FrameLandmarks":
        """
        Create a FrameLandmarks instance from a dictionary.
        """
        _landmarks = {
            name: Landmark(
                x=entry.get("x", 0.0),
                y=entry.get("y", 0.0),
                frame=frame_num,
                name=name
            )
            for name, entry in data.items()
        }
        return cls(frame=frame_num, landmarks=_landmarks)

    def get_landmark(self, landmark_name: str) -> Landmark:
        landmark = self.landmarks.get(landmark_name)
        if landmark is None:
            raise KeyError(f"Landmark '{landmark_name}' not found in frame {self.frame}")
        return landmark

    def get_landmarks(self) -> List[Landmark]:
        return list(self.landmarks.values())


class LandmarkData(BaseModel):
    """
    Encapsulates all landmark data for a given video.
    """
    frames: Dict[conint(ge=0), FrameLandmarks]

    @classmethod
    def from_dict(cls, data: Dict[int, Dict[str, Dict[str, float]]]) -> "LandmarkData":
        frames = {
            frame_num: FrameLandmarks.from_dict(frame_num, frame_data)
            for frame_num, frame_data in data.items()
        }
        return cls(frames=frames)

    def to_dict(self) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Convert LandmarkData to a dictionary format.
        """
        return {
            frame_num: {
                name: {
                    "x": landmark.x,
                    "y": landmark.y,
                }
                for name, landmark in frame_landmarks.landmarks.items()
            }
            for frame_num, frame_landmarks in self.frames.items()
        }

    def get_frame_landmarks(self, frame_num: int) -> FrameLandmarks:
        frame_landmarks = self.frames.get(frame_num)
        if frame_landmarks is None:
            raise KeyError(f"Frame {frame_num} not found")
        return frame_landmarks
