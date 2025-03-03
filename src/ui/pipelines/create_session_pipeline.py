# src/ui/workers/process_session_worker.py

from PyQt6.QtCore import QThread, pyqtSignal
from src.config import logger
from src.models.operation_controls import OperationControls
from src.modules.process_landmarks import ProcessLandmarks, CancellationException
from src.modules.annotate_video import AnnotateVideo
from src.utils.tokens import CancellationToken

class CreateSessionPipeline(QThread):
    progress_update = pyqtSignal(str, float)  # (stage, progress)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, app_context, parent=None):
        """
        app_context: Shared application context.
        """
        super().__init__(parent)
        self.token = CancellationToken()
        self.app_context = app_context
        self.session = app_context.current_session

    def run(self):
        try:
            # Local progress callback.
            def progress_cb(stage: str, progress: float):
                self.progress_update.emit(stage, progress)

            # === Step 1: Setup Session Directory ===
            setup_controls = OperationControls(
                overwrite=True,
                progress_callback=progress_cb,
                cancellation_token=self.token
            )
            self.app_context.session_manager.setup_session_directory(self.session, setup_controls)

            # === Process Landmarks ===
            processor_controls = OperationControls(
                overwrite=False,
                progress_callback=progress_cb,
                cancellation_token=self.token
            )
            processor = ProcessLandmarks()
            landmark_data = processor.run(
                raw_video_path=self.session.files.raw_video,
                video_metadata=self.session.video_metadata,
                mediapipe_preferences=self.session.mediapipe_preferences,
                operation_controls=processor_controls
            )

            self.app_context.data_io.save_landmark_data_to_file(
                file_path=self.session.files.landmark_data,
                landmark_data=landmark_data
            )

            # === Step 2: Annotate Video ===
            annotation_controls = OperationControls(
                overwrite=False,
                progress_callback=progress_cb,
                cancellation_token=self.token
            )
            annotator = AnnotateVideo()
            annotator.run(
                raw_video_path=self.session.files.raw_video,
                annotated_video_path=self.session.files.annotated_video,
                video_metadata=self.session.video_metadata,
                landmark_data=landmark_data,
                annotation_preferences=self.session.annotation_preferences,
                operation_controls=annotation_controls
            )

            self.finished.emit()

        except CancellationException:
            logger.info("Pipeline cancelled by user. Deleting session directory.")
            self.app_context.session_manager.delete_session(session=self.session)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            logger.warning(f"Pipeline failed with error (session has been deleted): {e}")
            self.app_context.session_manager.delete_session(session=self.session)

    def cancel(self):
        self.token.cancelled = True
