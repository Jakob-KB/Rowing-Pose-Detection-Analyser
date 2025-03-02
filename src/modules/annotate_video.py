# src/video_processing/annotate_video.py

import cv2
import numpy as np

from pathlib import Path
from typing import List

from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData, FrameLandmarks, Landmark
from src.models.video_metadata import VideoMetadata
from src.config import logger, cfg


class AnnotateVideo:
    landmark_connection: List = cfg.landmarks.connections
    reference_line_landmarks: List[str] = ["ankle", "hip"]

    def run(
            self,
            raw_video_path: Path,
            annotated_video_path: Path,
            video_metadata: VideoMetadata,
            landmark_data: LandmarkData,
            annotation_preferences: AnnotationPreferences,
            progress_callback = None
    ) -> None:
        """
        Annotate each frame of the raw video using landmark data from the YAML file.
        The annotated video is saved to the annotated_video_path specified in the session.
        """

        if annotation_preferences is None:
            raise ValueError("Annotation preferences not provided.")

        if landmark_data is None:
            raise ValueError("Landmark data not provided.")

        if video_metadata is None:
            raise ValueError("Video metadata not provided.")

        # Open raw input video stream
        cap = cv2.VideoCapture(str(raw_video_path))
        if not cap.isOpened():
            raise ValueError(f"Unable to open raw video stream from path {raw_video_path}")

        # Configure annotated output video stream
        out = cv2.VideoWriter(
            str(annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            video_metadata.fps,
            (video_metadata.width, video_metadata.height),
        )

        # Iterate through each frame
        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            try:
                frame_landmarks = landmark_data.get_frame_landmarks(frame_num)
                self.__annotate_frame(
                    frame,
                    frame_landmarks,
                    annotation_preferences,
                    )
            except KeyError:
                logger.warning(f"Frame {frame_num} not found in landmark data, skipping.")
                continue

            out.write(frame)

            if progress_callback:
                progress = (frame_num / video_metadata.total_frames) * 100
                if frame_num % 10 == 0 or frame_num == video_metadata.total_frames:
                    progress_callback("Annotating video", progress)

        cap.release()
        out.release()

        logger.info(f"Annotated video saved to {annotated_video_path}")


    def __annotate_frame(
            self,
            image: np.ndarray,
            frame_landmarks: FrameLandmarks,
            annotation_preferences: AnnotationPreferences
    ) -> None:
        """
        Draw landmarks and skeleton connections on the image.
        Returns a dict of drawn landmarks.
        """
        annotation_overlay = image.copy()

        # Draw each bone of the skeleton for each of the connected pairs of landmarks
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
                annotation_preferences.bone_colour,
                annotation_preferences.bone_thickness
            )

        # Draw each landmark as a point
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                annotation_overlay,
                landmark.get_position(),
                annotation_preferences.landmark_radius,
                annotation_preferences.landmark_colour,
                -1
            )

            # Draw reference line for selected landmarks
            if landmark.name in self.reference_line_landmarks:
                x, y = landmark.get_position()
                end_y = y - annotation_preferences.reference_line_length
                current_y = y

                # Calculate and draw dash segments of reference line
                while current_y > end_y:
                    segment_end = max(current_y - annotation_preferences.reference_line_dash_factor, end_y)
                    cv2.line(
                        annotation_overlay,
                        (x, current_y),
                        (x, segment_end),
                        annotation_preferences.reference_line_colour,
                        annotation_preferences.reference_line_thickness
                     )
                    current_y -= (annotation_preferences.reference_line_dash_factor * 2)

        # Overlay the annotation on the image with a set opacity
        alpha = annotation_preferences.opacity
        cv2.addWeighted(annotation_overlay, alpha, image, 1 - alpha, 0, image)
