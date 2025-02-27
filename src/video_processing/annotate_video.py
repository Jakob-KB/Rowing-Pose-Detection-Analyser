# src/video_processing/annotate_video.py
import cv2
import numpy as np
import yaml
from typing import Dict, Tuple, Any, List
from dataclasses import dataclass

from src import Session, AnnotationPrefs
from src.config import logger, cfg
from src.data_classes import *


class AnnotateVideo:
    def __init__(self, session: Session) -> None:
        # Store the session object
        self.session = session

        self.raw_video_path = self.session.paths.raw_video_path
        self.annotated_video_path = self.session.paths.annotated_video_path

        # ProcessLandmarks to draw reference lines for
        self.reference_line_landmarks: List[str] = ["ankle", "hip"]

        # Video metadata
        self.video_metadata = self.session.raw_video_metadata

        # Setup landmark data
        self.landmarks_data = self.session.load_landmark_data_from_session()
        self.landmark_connections = cfg.landmarks.connections


        # Setup annotation config (controls how annotations are drawn)
        self.annotation_prefs: AnnotationPrefs = self.session.annotation_prefs
        self.bone_prefs: AnnotationPrefs.BonePrefs = self.annotation_prefs.BonePrefs()
        self.landmark_prefs: AnnotationPrefs.LandmarkPrefs = self.annotation_prefs.LandmarkPrefs()
        self.reference_line_prefs: AnnotationPrefs.ReferenceLinePrefs = self.annotation_prefs.ReferenceLinePrefs()

    def run(self) -> None:
        """
        Annotate each frame of the raw video_metadata using landmark data from the YAML file.
        The annotated video_metadata is saved to the annotated_video_path specified in the session.
        """

        # Check that landmarks have been loaded
        if self.landmarks_data is None:
            logger.error("Video landmarks need to be loaded first.")

        # Open raw input video_metadata stream
        cap = cv2.VideoCapture(str(self.raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open raw video_metadata: {self.raw_video_path}")
            raise

        # Configure annotated output video_metadata stream
        out = cv2.VideoWriter(
            str(self.annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.video_metadata.fps,
            self.video_metadata.get_dimensions()
        )

        # Iterate through each frame
        total_frames = self.video_metadata.total_frames
        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            # Try to get the FrameLandmarks object from the dictionary
            frame_landmarks = self.landmarks_data.get_frame_landmarks(frame_num)
            if frame_landmarks is None:
                logger.warning(f"No landmark data for frame number {frame_num}")
            else:
                self.__annotate_frame(frame, frame_landmarks)

            out.write(frame)

        # Release input and output video_metadata streams
        cap.release()
        out.release()
        logger.info(f"Annotated video_metadata saved to {self.annotated_video_path}")

    def __annotate_frame(self, image: np.ndarray, frame_landmarks: FrameLandmarks):
        """
        Draw landmarks and skeleton connections on the image.
        Returns a dict of drawn landmarks.
        """
        # Create an overlay copy to draw the landmarks and lines
        overlay = image.copy()

        # Draw each bone of the skeleton for each of the connect landmarks
        for start_landmark_name, end_landmark_name in self.landmark_connections:
            start_landmark: Landmark = frame_landmarks.get_landmark(start_landmark_name)
            end_landmark: Landmark = frame_landmarks.get_landmark(end_landmark_name)

            start_point: Tuple[int, int] = start_landmark.get_screen_position(self.video_metadata)
            end_point: Tuple[int, int] = end_landmark.get_screen_position(self.video_metadata)

            cv2.line(
                image,
                start_point,
                end_point,
                self.bone_prefs.colour,
                self.bone_prefs.thickness
            )

        # Draw each landmark as a point
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                overlay,
                landmark.get_screen_position(self.video_metadata),
                self.landmark_prefs.radius,
                self.landmark_prefs.colour,
                -1
            )

            # Draw reference line for selected landmarks
            if landmark.name in self.reference_line_landmarks:
                x, y = landmark.get_screen_position(self.video_metadata)
                end_y = y - int(self.reference_line_prefs.length)
                current_y = y

                # Calculate and draw dash segments of reference line
                while current_y > end_y:
                    segment_end = max(current_y - self.reference_line_prefs.dash_factor, end_y)
                    cv2.line(
                        image,
                        (x, current_y),
                        (x, segment_end),
                        self.reference_line_prefs.colour,
                        self.reference_line_prefs.thickness
                     )
                    current_y -= (self.reference_line_prefs.dash_factor * 2)

        # Opacity blending
        alpha = self.annotation_prefs.opacity
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)




# Example usage:
if __name__ == "__main__":
    from src.session import Session
    from src.config import SESSIONS_DIR

    title = "athlete_1"
    session_folder = SESSIONS_DIR / title
    sample_session = Session.load_existing_session(session_folder)
    annotator = AnnotateVideo(sample_session)
    annotator.run()
