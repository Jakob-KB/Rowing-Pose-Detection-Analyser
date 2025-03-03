# src/simple_gui_pipeline.py

import shutil
import sys
from pathlib import Path

import mediapipe as mp
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QDialog
)

from src.config import DATA_DIR, logger
from src.models.operation_controls import OperationControls
from src.modules.session_manager import SessionManager
from src.modules.process_landmarks import ProcessLandmarks, CancellationException
from src.modules.annotate_video import AnnotateVideo
from src.modules.data_io import DataIO
from src.utils.tokens import CancellationToken


def create_pipeline_session():
    """
    Create a new session for the pipeline. If the session directory already exists,
    it will be removed.

    Returns:
        tuple: (session_manager, session)
    """
    session_manager = SessionManager()
    session_title = "sample_session_v0"
    original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
    session = session_manager.create_session(
        session_title=session_title,
        original_video_path=original_video_path
    )
    if session.directory.exists():
        shutil.rmtree(session.directory)
    return session_manager, session


class PipelineWorker(QThread):
    """
    Worker thread that performs session setup, landmark processing, and video annotation.
    Emits progress updates, finished, and error signals.
    """
    progress_update = pyqtSignal(str, float)  # (stage, progress)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, session_manager, session, parent=None):
        """
        Initialize the pipeline worker.

        Args:
            session_manager: The session manager instance.
            session: The session object.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.session_manager = session_manager
        self.session = session
        self.token = CancellationToken()

    def run(self):
        """Run the pipeline operations in a separate thread."""
        try:
            # Local progress callback to emit progress updates.
            def progress_cb(stage: str, progress: float):
                self.progress_update.emit(stage, progress)

            # === Step 1: Setup Session Directory ===
            setup_controls = OperationControls(
                overwrite=True,
                progress_callback=progress_cb,
                cancellation_token=self.token
            )
            self.session_manager.setup_session_directory(self.session, setup_controls)

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

            data_io = DataIO()
            data_io.save_landmark_data_to_file(
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
            self.session_manager.delete_session(session=self.session)
            # Emit finished signal even on cancellation so that the dialog can clean up.
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            logger.warning(f"Pipeline failed with error (session has been deleted): {e}")
            self.session_manager.delete_session(session=self.session)

    def cancel(self):
        """Signal the worker to cancel its operations."""
        self.token.cancelled = True


class PipelineDialog(QDialog):
    """
    Dialog window that displays the pipeline progress and allows cancellation.
    The dialog disables the window close button and waits for the worker thread to finish.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Disable the close ("X") button.
        flags = self.windowFlags()
        flags &= ~Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)

        self.setWindowTitle("Pipeline Progress")
        self.resize(300, 150)

        # Layout and widgets.
        self.layout = QVBoxLayout(self)
        self.progress_label = QLabel("Starting pipeline...", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.cancel_btn = QPushButton("Cancel Pipeline", self)

        self.layout.addWidget(self.progress_label)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.cancel_btn)

        # Flag to track if cancellation has been requested.
        self.cancel_requested = False

        # Create a new session for the pipeline.
        self.session_manager, self.session = create_pipeline_session()

        # Initialize and connect the pipeline worker.
        self.worker = PipelineWorker(self.session_manager, self.session, self)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.cancel_btn.clicked.connect(self.cancel_pipeline)

        # Start the worker thread.
        self.worker.start()

    def update_progress(self, stage: str, progress: float):
        """Update the progress label and progress bar."""
        self.progress_label.setText(f"{stage}: {progress:.2f}%")
        self.progress_bar.setValue(int(progress))

    def on_finished(self):
        """Handle worker finished signal."""
        if self.cancel_requested:
            self.close()
        else:
            self.progress_label.setText("Pipeline finished!")
            self.cancel_btn.setEnabled(False)

    def on_error(self, err: str):
        """Handle errors emitted by the worker."""
        self.progress_label.setText(f"Error: {err}")
        if self.cancel_requested:
            self.close()

    def cancel_pipeline(self):
        """Initiate cancellation of the pipeline."""
        if not self.worker.token.cancelled:
            self.cancel_requested = True
            self.worker.cancel()
            self.progress_label.setText("Cancelling pipeline...")
            self.cancel_btn.setEnabled(False)
            # Wait for the worker to finish before closing the dialog.


class MainWindow(QWidget):
    """
    Main window that displays a single 'Start' button.
    Clicking the button opens the pipeline dialog.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Pipeline")
        self.setFixedSize(400, 400)
        self.layout = QVBoxLayout(self)

        self.start_btn = QPushButton("Start", self)
        self.layout.addStretch(1)
        self.layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addStretch(1)

        self.start_btn.clicked.connect(self.open_pipeline_dialog)

    def open_pipeline_dialog(self):
        """Open the pipeline progress dialog modally."""
        dialog = PipelineDialog(self)
        dialog.exec()


def main():
    """Entry point of the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
