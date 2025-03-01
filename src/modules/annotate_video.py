# src/video_processing/annotate_video.py
import cv2
import numpy as np
from pathlib import Path

from typing import List, Tuple

from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData, FrameLandmarks, Landmark
from src.config import logger, cfg


class AnnotateVideo:
    landmark_connection: List = cfg.landmarks.connections
    reference_line_landmarks: List[str] = ["ankle", "hip"]
    annotation_prefs: AnnotationPreferences = None

    def run(
            self,
            raw_video_path: Path,
            annotated_video_path: Path,
            landmark_data: LandmarkData,
            annotation_preferences: AnnotationPreferences
    ) -> None:
        """
        Annotate each frame of the raw video_metadata using landmark data from the YAML file.
        The annotated video_metadata is saved to the annotated_video_path specified in the session.
        """

        self.annotation_prefs = annotation_preferences

        if self.annotation_prefs is None:
            logger.error("Annotation preferences not set.")
            return

        if landmark_data is None:
            logger.error("No landmark data was loaded.")
            return

        # Open raw input video_metadata stream
        cap = cv2.VideoCapture(str(raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open raw video_metadata: {raw_video_path}")
            raise

        # Configure annotated output video_metadata stream
        out = cv2.VideoWriter(
            str(annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            cfg.video.fps,
            (cfg.video.width, cfg.video.height)
        )
        # TODO: Handle hard use case of cfg here, or at least reference it

        # Iterate through each frame
        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            # Try to get the FrameLandmarks object from the dictionary
            frame_landmarks = landmark_data.get_frame_landmarks(frame_num)
            if frame_landmarks is None:
                logger.warning(f"No landmark data for frame number {frame_num}")
            else:
                self.__annotate_frame(frame, frame_landmarks)

            out.write(frame)

        # Release input and output video_metadata streams
        cap.release()
        out.release()

        # Reset annotation preferences to None
        self.annotation_prefs = None

        logger.info(f"Annotated video_metadata saved to {annotated_video_path}")


    def __annotate_frame(self, image: np.ndarray, frame_landmarks: FrameLandmarks) -> None:
        """
        Draw landmarks and skeleton connections on the image.
        Returns a dict of drawn landmarks.
        """
        # Create an overlay copy to draw the landmarks and lines
        overlay = image.copy()

        # Draw each bone of the skeleton for each of the connect landmarks
        for start_landmark_name, end_landmark_name in self.landmark_connection:
            start_landmark: Landmark = frame_landmarks.get_landmark(start_landmark_name)
            end_landmark: Landmark = frame_landmarks.get_landmark(end_landmark_name)

            start_point: Tuple[int, int] = start_landmark.get_screen_position()
            end_point: Tuple[int, int] = end_landmark.get_screen_position()

            cv2.line(
                overlay,
                start_point,
                end_point,
                self.annotation_prefs.bone_colour,
                self.annotation_prefs.bone_thickness
            )

        # Draw each landmark as a point
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                overlay,
                landmark.get_screen_position(),
                self.annotation_prefs.landmark_radius,
                self.annotation_prefs.landmark_colour,
                -1
            )

            # Draw reference line for selected landmarks
            if landmark.name in self.reference_line_landmarks:
                x, y = landmark.get_screen_position()
                end_y = y - self.annotation_prefs.reference_line_length
                current_y = y

                # Calculate and draw dash segments of reference line
                while current_y > end_y:
                    segment_end = max(current_y - self.annotation_prefs.reference_line_dash_factor, end_y)
                    cv2.line(
                        overlay,
                        (x, current_y),
                        (x, segment_end),
                        self.annotation_prefs.reference_line_colour,
                        self.annotation_prefs.reference_line_thickness
                     )
                    current_y -= (self.annotation_prefs.reference_line_dash_factor * 2)

        # Opacity blending
        alpha = self.annotation_prefs.opacity
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)
