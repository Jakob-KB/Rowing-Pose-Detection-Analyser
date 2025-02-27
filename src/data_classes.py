# src/data_classes.py
from dataclasses import dataclass
from typing import Dict, List, Tuple
from src.config import cfg, logger
from pathlib import Path

@dataclass
class AnnotationPrefs:
    opacity: float = cfg.annotation_prefs.opacity

    @dataclass
    class BonePrefs:
        colour: Tuple[int, int, int] = tuple(cfg.annotation_prefs.bone.colour)
        thickness: int = cfg.annotation_prefs.bone.thickness

    @dataclass
    class LandmarkPrefs:
        colour: Tuple[int, int, int] = tuple(cfg.annotation_prefs.landmark.colour)
        radius: int = cfg.annotation_prefs.landmark.radius

    @dataclass
    class ReferenceLinePrefs:
        length: int = cfg.annotation_prefs.reference_line.length
        colour: Tuple[int, int, int] = tuple(cfg.annotation_prefs.reference_line.colour)
        thickness: int = cfg.annotation_prefs.reference_line.thickness
        dash_factor: int = cfg.annotation_prefs.reference_line.dash_factor

@dataclass
class MediapipePreferences:
    model_complexity: int = cfg.mediapipe.model_complexity
    smooth_landmarks: bool = cfg.mediapipe.smooth_landmarks
    min_detection_confidence: float = cfg.mediapipe.min_detection_confidence
    min_tracking_confidence: float = cfg.mediapipe.min_tracking_confidence

@dataclass
class VideoMetadata:
    total_frames: int
    width: int
    height: int
    fps: float

    def get_dimensions(self) -> Tuple[int, int]:
        return self.width, self.height

@dataclass
class SessionPaths:
    session_dir: Path
    raw_video_path: Path
    annotated_video_path: Path
    landmark_data_path: Path
    analysis_data_path: Path
    session_config_path: Path

@dataclass
class Landmark:
    """
    Represents a single landmark with normalized coordinates (x, y) and visibility.
    """
    x: float
    y: float
    visibility: float
    frame: int
    name: str


    def get_screen_position(self, video: "VideoMetadata") -> Tuple[int, int]:
        """
        Convert normalized coordinates to pixel positions based on video_metadata dimensions.
        """
        return int(video.width * self.x), int(video.height * self.y)

@dataclass
class FrameLandmarks:
    """
    Encapsulates landmarks for a single frame.

    This class stores landmarks in a dictionary, indexed by their integer mapping.
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
            raise KeyError()

    def get_landmarks(self) -> List[Landmark]:
        return list(self.landmarks.values())

@dataclass
class LandmarkData:
    frames: Dict[int, FrameLandmarks]

    @classmethod
    def from_dict(cls, data: Dict[int, Dict[str, Dict[str, float]]]):
        frames = {
            frame_num: FrameLandmarks.from_dict(frame_num, frame_data)
            for frame_num, frame_data in data.items()
        }
        return cls(frames)

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
