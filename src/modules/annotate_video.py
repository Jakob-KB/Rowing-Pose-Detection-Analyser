# src/modules/annotate_video.py

import cv2
import numpy as np
from pathlib import Path
from typing import List

from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData, FrameLandmarks, Landmark
from src.models.video_metadata import VideoMetadata
from src.config import logger, cfg


class AnnotateVideo:
    landmark_connection:List = cfg.landmarks.connections
    reference_line_landmarks: List[str] = ["ankle", "hip"]

    def __init__(self, annotation_preferences: AnnotationPreferences=AnnotationPreferences()) -> None:
        self.annotation_preferences: AnnotationPreferences = annotation_preferences

    def run(self,
            raw_video_path: Path,
            annotated_video_path: Path,
            video_metadata: VideoMetadata,
            landmark_data: LandmarkData
            ) -> None:
        """
        Annotate each frame of the raw video using landmark data.
        """
        if self.annotation_preferences is None:
            raise ValueError("Annotation preferences not provided.")
        if landmark_data is None:
            raise ValueError("Landmark data not provided.")
        if video_metadata is None:
            raise ValueError("Video metadata not provided.")

        if annotated_video_path.exists():
            raise FileExistsError(
                f"Annotated video already exists at path {annotated_video_path}"
            )

        # Open raw input video stream.
        cap = cv2.VideoCapture(str(raw_video_path))
        if not cap.isOpened():
            raise ValueError(f"Unable to open raw video stream from path {raw_video_path}")

        # Configure annotated output video stream.
        out = cv2.VideoWriter(
            str(annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            video_metadata.fps,
            video_metadata.get_dimensions(),
        )

        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            try:
                frame_landmarks: FrameLandmarks = landmark_data.get_frame_landmarks(frame_num)
                self.__annotate_frame(frame, frame_landmarks)
            except KeyError:
                logger.warning(f"Frame {frame_num} not found in landmark data, skipping.")
                continue

            out.write(frame)

        cap.release()
        out.release()

        logger.info(f"Annotated video saved to {annotated_video_path}")

    def __annotate_frame(
        self,
        image: np.ndarray,
        frame_landmarks: FrameLandmarks
    ) -> None:
        annotation_overlay = image.copy()

        # Draw each bone of the skeleton for each connected pair of landmarks.
        for start_landmark_name, end_landmark_name in self.landmark_connection:
            try:
                start_landmark: Landmark = frame_landmarks.get_landmark(start_landmark_name)
                end_landmark: Landmark = frame_landmarks.get_landmark(end_landmark_name)
            except KeyError:
                logger.warning(f"Landmark {start_landmark_name} or {end_landmark_name} not found in frame, skipping.")
                continue

            cv2.line(
                annotation_overlay,
                start_landmark.get_position(),
                end_landmark.get_position(),
                self.annotation_preferences.bone_colour,
                self.annotation_preferences.bone_thickness
            )

        # Draw each landmark as a point.
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                annotation_overlay,
                landmark.get_position(),
                self.annotation_preferences.landmark_radius,
                self.annotation_preferences.landmark_colour,
                -1
            )

            # Draw reference line for selected landmarks.
            if landmark.name in self.reference_line_landmarks:
                x, y = landmark.get_position()
                end_y = y - self.annotation_preferences.reference_line_length
                current_y = y

                # Draw dashed reference line.
                while current_y > end_y:
                    segment_end = max(current_y - self.annotation_preferences.reference_line_dash_factor, end_y)
                    cv2.line(
                        annotation_overlay,
                        (x, current_y),
                        (x, segment_end),
                        self.annotation_preferences.reference_line_colour,
                        self.annotation_preferences.reference_line_thickness
                    )
                    current_y -= (self.annotation_preferences.reference_line_dash_factor * 2)

        # Overlay the annotation with opacity.
        alpha = self.annotation_preferences.opacity
        cv2.addWeighted(annotation_overlay, alpha, image, 1 - alpha, 0, image)

    def update_annotation_preferences(self, annotation_preferences: AnnotationPreferences) -> None:
        self.annotation_preferences = annotation_preferences
