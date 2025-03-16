# src/modules/annotate_video.py

import cv2
import numpy as np
from pathlib import Path
from typing import List

from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData, FrameLandmarks, Landmark
from src.models.video_metadata import VideoMetadata
from src.config import logger, cfg
from src.utils.status_callback import status_callback
from src.utils.exceptions import ProcessCancelled


class VideoAnnotator:
    landmark_connection: List = cfg.landmarks.connections
    reference_line_landmarks: List[str] = ["ankle", "hip"]

    cancellation_message = "Cancelled."
    success_message = "Success."

    def __init__(self, annotation_preferences: AnnotationPreferences = AnnotationPreferences()) -> None:
        self.annotation_preferences: AnnotationPreferences = annotation_preferences
        self._is_cancelled = False

    def run(
        self,
        raw_video_path: Path,
        annotated_video_path: Path,
        video_metadata: VideoMetadata,
        landmark_data: LandmarkData,
        status=status_callback
    ) -> None:
        self._is_cancelled = False

        cap = None
        out = None

        try:
            self._update_status(status,"Starting video annotation.")

            # Open raw video stream
            cap = cv2.VideoCapture(str(raw_video_path))
            if not cap.isOpened():
                raise ValueError(f"Unable to open raw video stream from path {raw_video_path}")

            # Configure annotated output video stream
            out = cv2.VideoWriter(
                str(annotated_video_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                video_metadata.fps,
                video_metadata.get_dimensions(),
            )

            frame_num = 0

            while True:
                if self._is_cancelled:
                    raise ProcessCancelled(self.cancellation_message)

                ret, frame = cap.read()
                if not ret:
                    break

                frame_num += 1

                try:
                    frame_landmarks: FrameLandmarks = landmark_data.get_frame_landmarks(frame_num)
                    # Call the static method, passing in annotation preferences.
                    VideoAnnotator.__annotate_frame(frame, frame_landmarks, self.annotation_preferences)
                except KeyError:
                    logger.warning(f"Frame {frame_num} not found in landmark data, skipping.")
                    continue

                out.write(frame)

                progress_value = (
                    frame_num / video_metadata.total_frames * 100
                    if hasattr(video_metadata, "total_frames") and video_metadata.total_frames > 0
                    else 0
                )
                self._update_status(status,f"Annotating Video", progress_value)

            cap.release()
            out.release()

            if self._is_cancelled:
                raise ProcessCancelled(self.cancellation_message)

            self._update_status(status, self.success_message)

        except ProcessCancelled as e:
            logger.info("Annotation process cancelled.")
            self._handle_unexpected_exit(annotated_video_path, cap, out)
            raise ProcessCancelled(e)
        except Exception as e:
            logger.error(f"Error annotating video: {e}")
            self._handle_unexpected_exit(annotated_video_path, cap, out)
            raise Exception(e)

    def cancel(self) -> None:
        self._is_cancelled = True

    @staticmethod
    def __annotate_frame(
        image: np.ndarray,
        frame_landmarks: FrameLandmarks,
        annotation_preferences: AnnotationPreferences
    ) -> None:
        annotation_overlay = image.copy()

        # Draw skeleton connections.
        for start_landmark_name, end_landmark_name in VideoAnnotator.landmark_connection:
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

        # Draw landmarks and reference lines.
        for landmark in frame_landmarks.get_landmarks():
            cv2.circle(
                annotation_overlay,
                landmark.get_position(),
                annotation_preferences.landmark_radius,
                annotation_preferences.landmark_colour,
                -1
            )

            if landmark.name in VideoAnnotator.reference_line_landmarks:
                x, y = landmark.get_position()
                end_y = y - annotation_preferences.reference_line_length
                current_y = y

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

        # Overlay annotations with opacity.
        alpha = annotation_preferences.opacity
        cv2.addWeighted(annotation_overlay, alpha, image, 1 - alpha, 0, image)

    @staticmethod
    def _update_status(status_callback_function, message: str, progress_value: float = None) -> None:
        if status_callback_function:
            status_callback_function(message=message, progress_value=progress_value)

    @staticmethod
    def _handle_unexpected_exit(annotated_video_path: Path, cap: cv2.VideoCapture = None, out: cv2.VideoWriter = None) -> None:
        # Release video capture and writer resources
        if cap is not None:
            cap.release()
        if out is not None:
            out.release()
        # Remove the partially written annotated file if it exists
        if annotated_video_path.exists():
            try:
                annotated_video_path.unlink()
                logger.info(f"Partially annotated file {annotated_video_path} removed.")
            except Exception as e:
                logger.error(f"Error removing file {annotated_video_path}: {e}")
