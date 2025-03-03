# src/ui/workers/process_session_worker.py
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from src.config import logger
from src.models.operation_controls import OperationControls
from src.modules.process_landmarks import ProcessLandmarks, CancellationException
from src.modules.annotate_video import AnnotateVideo
from src.utils.tokens import CancellationToken

class LoadSessionPipeline(QThread):
    progress_update = pyqtSignal(str, float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, app_context, session_directory: Path, parent=None):
        """
        app_context: Shared application context.
        """
        super().__init__(parent)
        self.token = CancellationToken()
        self.app_context = app_context
        self.session_directory = session_directory

    def run(self):
        try:
            # Local progress callback.
            def progress_cb(stage: str, progress: float):
                self.progress_update.emit(stage, progress)

            self.app_context.current_session = self.app_context.session_manager.load_session(
                session_directory=self.session_directory,
                operation_controls=OperationControls(
                    overwrite=False,
                    progress_callback=progress_cb,
                    cancellation_token=self.token
                )
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
