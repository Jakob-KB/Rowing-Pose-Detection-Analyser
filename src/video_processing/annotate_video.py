# src/video_processing/annotate_video.py
import cv2
import numpy as np
import yaml
from typing import Dict, Tuple, Any, List
from dataclasses import dataclass

from src import Session
from src.analysis.back_detection import landmarks
from src.config import logger, cfg


@dataclass
class AnnotationConfig:
    opacity: float = cfg.annotation.opacity

    @dataclass
    class BoneAnnotation:
        colour: Tuple[int, int, int] = cfg.annotation.skeleton_bone_colour
        thickness: int = cfg.annotation.skeleton_bone_thickness

    @dataclass
    class LandmarkAnnotation:
        colour: Tuple[int, int, int] = cfg.annotation.landmark_point_colour
        radius: int = cfg.annotation.landmark_point_radius

@dataclass
class VerticalReferenceLine:
    landmark: Tuple[int, int]
    length: int = 96 # 96 is default (12 * dot_factor)
    color: Tuple[int, int, int] = (255, 255, 255)
    thickness: int = 3
    dot_factor: int = 8

@dataclass
class VideoMetadata:
    width: int = cfg.video.width
    height: int = cfg.video.height
    fps: int = cfg.video.fps

    def get_dimensions(self) -> Tuple[int, int]:
        return self.width, self.height

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
        Convert normalized coordinates to pixel positions based on video dimensions.
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
class VideoLandmarks:
    """
    Stores landmarks for an entire video.

    This class manages multiple frames, each containing its own set of landmarks.
    """
    frames: Dict[int, FrameLandmarks]

    @classmethod
    def from_dict(cls, data: Dict[int, Dict[str, Dict[str, float]]], landmarks_map: Dict[str, int]):
        """
        Creates a VideoLandmarks object from a dictionary of landmark data.

        :param data: Dictionary mapping frame numbers to their respective landmark data.
        :param landmarks_map: Mapping of landmark names to integer indices.
        :return: VideoLandmarks object containing all frame landmarks.
        """
        frames = {
            frame_num: FrameLandmarks.from_dict(frame_data, landmarks_map)
            for frame_num, frame_data in data.items()
        }
        return cls(frames)

    def get_frame_landmarks(self, frame_num: int) -> FrameLandmarks:
        if frame_num in self.frames:
            return self.frames[frame_num]
        else:
            logger.error(f"Failed to get landmarks for frame {frame_num}")
            raise KeyError(f"Frame {frame_num} not found")


class AnnotateVideo:
    def __init__(self, session: Session) -> None:
        # Store the session object
        self.session = session

        # Landmarks to draw reference lines for
        self.reference_line_landmarks: List[str] = ["ankle", "hip"]

        # Landmark name to id mapping as well as bone connections
        self.landmarks_mapping = cfg.landmarks.mapping
        self.landmark_connections = cfg.landmarks.connections

        # Video metadata
        self.video = VideoMetadata()

        self.video_landmarks = None
        self.load_landmark_data()

        # Setup annotation config (controls how annotations are drawn)
        self.annotation_config = AnnotationConfig()
        self.bone_annotation = self.annotation_config.BoneAnnotation()
        self.landmark_annotation = self.annotation_config.LandmarkAnnotation()


    def load_landmark_data(self) -> None:
        try:
            # Load landmark data from YAML
            with open(self.session.landmark_data_path, "r") as f:
                yaml_landmarks = yaml.safe_load(f)

            # Map landmark data by frame
            self.video_landmarks = VideoLandmarks.from_dict(
                data={entry["frame"]: entry["landmarks"] for entry in yaml_landmarks},
                landmarks_map=self.landmarks_mapping
            )
        except Exception as e:
            logger.error(f"Unexpected error while loading landmark data: {e}")
            raise

    def annotate_video(self) -> None:
        """
        Annotate each frame of the raw video using landmark data from the YAML file.
        The annotated video is saved to the annotated_video_path specified in the session.
        """

        # Check that landmarks have been loaded
        if self.video_landmarks is None:
            logger.error("Video landmarks need to be loaded first")

        # Open raw input video stream
        cap = cv2.VideoCapture(str(self.session.raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open raw video: {self.session.raw_video_path}")
            raise

        # Configure annotated output video stream
        out = cv2.VideoWriter(
            str(self.session.annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.video.fps,
            self.video.get_dimensions()
        )

        # Iterate through each frame
        frame_num = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            # Retrieve landmarks for the current frame
            try:
                frame_landmarks = self.video_landmarks.get_frame(frame_num)
                self.__annotate_frame(frame, frame_landmarks)
            except KeyError:
                logger.error(f"No landmark data for this frame. Frame number '{frame_num}'.")
                pass

            out.write(frame)

        # Release input and output video streams
        cap.release()
        out.release()
        logger.info(f"Annotated video saved to {self.session.annotated_video_path}")

    def __annotate_frame(self, image: np.ndarray, frame_landmarks: FrameLandmarks) -> Dict[str, Dict[str, float]]:
        """
        Draw landmarks and skeleton connections on the image.
        Returns a dict of drawn landmarks.
        """
        # Create an overlay copy to draw the landmarks and lines
        overlay = image.copy()

        # Draw each bone of the skeleton for each of the connect landmarks
        for start_landmark_id, end_landmark_id in self.landmark_connections:
            start_landmark: Landmark = frame_landmarks.get_landmark(start_landmark_id)
            end_landmark: Landmark = frame_landmarks.get_landmark(end_landmark_id)

            start_point: Tuple[int, int] = start_landmark.get_screen_position(self.video)
            end_point: Tuple[int, int] = end_landmark.get_screen_position(self.video)

            cv2.line(
                image,
                start_point,
                end_point,
                self.bone_annotation.colour,
                self.bone_annotation.thickness
            )

        # Draw each landmark as a point
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                overlay,
                landmark.get_screen_position(self.video),
                self.landmark_annotation.radius,
                self.landmark_annotation.colour,
                -1
            )

            # Draw reference line for selected landmarks
            if landmark. in self.reference_line_landmarks:
                dotted_line = VerticalReferenceLine(landmark)
                self._draw_vertical_reference_line(overlay, dotted_line)

        # Opacity blending
        alpha = self.annotation_config.opacity
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

        return frame_landmarks_RENAME

    @staticmethod
    def _draw_vertical_reference_line(image: np.ndarray, vertical_reference_line: VerticalReferenceLine) -> None:
        """
        Draw a vertical reference line from a given landmark.
        """
        dot_length: int = 8
        gap: int = 8

        x, y = vertical_reference_line.landmark
        end_y = y - vertical_reference_line.length
        current_y = y

        while current_y > end_y:
            # Calculate the end of the current dot segment
            segment_end = max(current_y - dot_length, end_y)
            cv2.line(image,
                     (x, current_y),
                     (x, segment_end),
                     vertical_reference_line.color,
                     vertical_reference_line.thickness
                     )
            current_y -= (dot_length + gap)

    def _landmark_position_to_pixel_position(self, landmark: Any) -> Tuple[int, int]:

        # Calculate the position of the landmark relative to the videos dimensions
        landmark_pixel_pos_x = int(self.video.width * landmark.x)
        landmark_pixel_pos_y = int(self.video.height * landmark.y)

        return landmark_pixel_pos_x, landmark_pixel_pos_y



# Example usage:
if __name__ == "__main__":
    from src.session import Session
    from src.config import SESSIONS_DIR

    title = "athlete_1"
    session_folder = SESSIONS_DIR / title
    sample_session = Session.load_existing_session(session_folder)
    annotator = AnnotateVideo(sample_session)
    annotator.annotate_video()
