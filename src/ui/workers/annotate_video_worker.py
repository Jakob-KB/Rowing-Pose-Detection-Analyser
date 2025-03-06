import cv2
import numpy as np
from pathlib import Path
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData, FrameLandmarks, Landmark
from src.models.video_metadata import VideoMetadata
from src.config import logger, cfg

class AnnotateVideoWorker(QThread):
    progress = pyqtSignal(str, int)  # (status message, progress percentage)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    # Using configuration values for connections and reference landmarks.
    landmark_connection: List = cfg.landmarks.connections
    reference_line_landmarks: List[str] = ["ankle", "hip"]

    def __init__(
        self,
        raw_video_path: Path,
        annotated_video_path: Path,
        video_metadata: VideoMetadata,
        landmark_data: LandmarkData,
        annotation_preferences: AnnotationPreferences = AnnotationPreferences(),
        parent=None
    ) -> None:
        super().__init__(parent)
        self.raw_video_path: Path = raw_video_path
        self.annotated_video_path: Path = annotated_video_path
        self.video_metadata: VideoMetadata = video_metadata
        self.landmark_data: LandmarkData = landmark_data
        self.annotation_preferences: AnnotationPreferences = annotation_preferences

        self._is_canceled: bool = False

    def cancel(self):
        """Signal the thread to cancel its work."""
        self._is_canceled = True

    def _cleanup(self):
        """Remove the annotated video file if it exists."""
        if self.annotated_video_path.exists():
            self.annotated_video_path.unlink()
            logger.info(f"Annotated video remnants deleted.")

    def run(self):
        try:
            # Validate inputs.
            if self.annotation_preferences is None:
                raise ValueError("Annotation preferences not provided.")
            if self.landmark_data is None:
                raise ValueError("Landmark data not provided.")
            if self.video_metadata is None:
                raise ValueError("Video metadata not provided.")
            if self.annotated_video_path.exists():
                raise FileExistsError(
                    f"Annotated video already exists at path {self.annotated_video_path}"
                )

            # Open the raw video stream.
            cap = cv2.VideoCapture(str(self.raw_video_path))
            if not cap.isOpened():
                raise ValueError(f"Unable to open raw video stream from path {self.raw_video_path}")

            # Configure the annotated video output stream.
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(
                str(self.annotated_video_path),
                fourcc,
                self.video_metadata.fps,
                self.video_metadata.get_dimensions()
            )

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_num = 0

            while True:
                # Check for cancellation before processing a frame.
                if self._is_canceled:
                    cap.release()
                    out.release()
                    self._cleanup()
                    self.canceled.emit()
                    return

                ret, frame = cap.read()
                if not ret:
                    break

                frame_num += 1

                try:
                    # Get landmark data for the current frame.
                    frame_landmarks: FrameLandmarks = self.landmark_data.get_frame_landmarks(frame_num)
                    self.__annotate_frame(frame, frame_landmarks)
                except KeyError:
                    logger.warning(f"Frame {frame_num} not found in landmark data, skipping.")
                    # Optionally, write the frame unannotated.
                    pass

                out.write(frame)

                # Update progress every 10 frames.
                if total_frames > 0 and frame_num % 10 == 0:
                    progress_percent = int((frame_num / total_frames) * 100)
                    self.progress.emit("Annotating video", progress_percent)

            cap.release()
            out.release()

            logger.info(f"Annotated video saved to {self.annotated_video_path}")
            self.finished.emit()

        except Exception as e:
            error_msg = f"Error processing video: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def __annotate_frame(
        self,
        image: np.ndarray,
        frame_landmarks: FrameLandmarks
    ) -> None:
        # Create an overlay to draw annotations.
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

                # Draw a dashed reference line.
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

        # Blend the annotation overlay with the original image.
        alpha = self.annotation_preferences.opacity
        cv2.addWeighted(annotation_overlay, alpha, image, 1 - alpha, 0, image)
