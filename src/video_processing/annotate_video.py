# src/video_processing/annotate_video.py
import cv2
import numpy as np

from src import Session
from src.landmark_dataclasses import *


class AnnotateVideo:
    def __init__(self, session: Session) -> None:
        # Store the session object
        self.session = session

        # ProcessLandmarks to draw reference lines for
        self.reference_line_landmarks: List[str] = ["ankle", "hip"]

        # Setup landmark data
        self.landmarks_data = self.session.load_landmark_data_from_session()


    def run(self) -> None:
        """
        Annotate each frame of the raw video_metadata using landmark data from the YAML file.
        The annotated video_metadata is saved to the annotated_video_path specified in the session.
        """

        # Check that landmarks have been loaded
        if self.landmarks_data is None:
            logger.error("Video landmarks need to be loaded first.")

        # Open raw input video_metadata stream
        cap = cv2.VideoCapture(str(self.session.raw_video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open raw video_metadata: {self.session.raw_video_path}")
            raise

        # Configure annotated output video_metadata stream
        out = cv2.VideoWriter(
            str(self.session.annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            cfg.video.fps,
            (cfg.video.width, cfg.video.height)
        )

        # Iterate through each frame
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
        logger.info(f"Annotated video_metadata saved to {self.session.annotated_video_path}")

    def __annotate_frame(self, image: np.ndarray, frame_landmarks: FrameLandmarks) -> None:
        """
        Draw landmarks and skeleton connections on the image.
        Returns a dict of drawn landmarks.
        """
        # Create an overlay copy to draw the landmarks and lines
        overlay = image.copy()

        # Draw each bone of the skeleton for each of the connect landmarks
        for start_landmark_name, end_landmark_name in cfg.landmarks.connections:
            start_landmark: Landmark = frame_landmarks.get_landmark(start_landmark_name)
            end_landmark: Landmark = frame_landmarks.get_landmark(end_landmark_name)

            start_point: Tuple[int, int] = start_landmark.get_screen_position()
            end_point: Tuple[int, int] = end_landmark.get_screen_position()

            cv2.line(
                overlay,
                start_point,
                end_point,
                tuple(cfg.annotation_prefs.bone.colour),
                cfg.annotation_prefs.bone.thickness
            )

        # Draw each landmark as a point
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                overlay,
                landmark.get_screen_position(),
                cfg.annotation_prefs.landmark.radius,
                cfg.annotation_prefs.landmark.colour,
                -1
            )

            # Draw reference line for selected landmarks
            if landmark.name in self.reference_line_landmarks:
                x, y = landmark.get_screen_position()
                end_y = y - cfg.annotation_prefs.reference_line.length
                current_y = y

                # Calculate and draw dash segments of reference line
                while current_y > end_y:
                    segment_end = max(current_y - cfg.annotation_prefs.reference_line.dash_factor, end_y)
                    cv2.line(
                        overlay,
                        (x, current_y),
                        (x, segment_end),
                        cfg.annotation_prefs.reference_line.colour,
                        cfg.annotation_prefs.reference_line.thickness
                     )
                    current_y -= (cfg.annotation_prefs.reference_line.dash_factor * 2)

        # Opacity blending
        alpha = cfg.annotation_prefs.opacity
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
