# src/create_session_pipeline.py

import shutil
import sys

import mediapipe as mp
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QDialog
)

from src.config import DATA_DIR, logger
from src.modules.session_manager import SessionManager, SessionSetup
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.annotate_video import AnnotateVideo
from src.utils.exceptions import CancellationException
from src.modules.data_io import DataIO


def create_pipeline_session():
    """
    Create a new session for the pipeline. If the session directory already exists,
    it will be removed.
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
        super().__init__(parent)
        self.session_manager = session_manager
        self.session = session

        # We'll keep references to the cancelable tasks for cancellation.
        self.session_setup = None
        self.landmark_processor = None
        self.video_annotator = None

    def run(self):
        try:
            # Local lambda for progress updates.
            progress_cb = lambda stage, progress: self.progress_update.emit(stage, progress)

            # === Step 1: Setup Session Directory ===
            self.session_setup = SessionSetup(self.session)
            self.session_setup.set_progress_callback(progress_cb)
            self.session_setup.run()

            # === Step 2: Process Landmarks ===
            self.landmark_processor = ProcessLandmarks(
                raw_video_path=self.session.files.raw_video,
                video_metadata=self.session.video_metadata,
                mediapipe_preferences=self.session.mediapipe_preferences
            )
            self.landmark_processor.set_progress_callback(progress_cb)
            landmark_data = self.landmark_processor.run()

            # Save landmark data.
            DataIO().save_landmark_data_to_file(
                file_path=self.session.files.landmark_data,
                landmark_data=landmark_data
            )

            # === Step 3: Annotate Video ===
            self.video_annotator = AnnotateVideo(
                raw_video_path=self.session.files.raw_video,
                annotated_video_path=self.session.files.annotated_video,
                video_metadata=self.session.video_metadata,
                landmark_data=landmark_data,
                annotation_preferences=self.session.annotation_preferences,
                overwrite=False
            )
            self.video_annotator.set_progress_callback(progress_cb)
            self.video_annotator.run()

            self.finished.emit()

        except CancellationException:
            logger.info("Pipeline cancelled by user. Deleting session directory.")
            self.session_manager.delete_session(session=self.session)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            logger.warning(f"Pipeline failed with error (session deleted): {e}")
            self.session_manager.delete_session(session=self.session)

    def cancel(self):
        """Cancel any active task in the pipeline."""
        if self.session_setup:
            self.session_setup.cancel()
        if self.landmark_processor:
            self.landmark_processor.cancel()
        if self.video_annotator:
            self.video_annotator.cancel()


class PipelineDialog(QDialog):
    """
    Dialog window that displays the pipeline progress and allows cancellation.
    The dialog disables the window close button and waits for the pipeline thread to finish.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        flags = self.windowFlags()
        flags &= ~Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)

        self.setWindowTitle("Pipeline Progress")
        self.resize(300, 150)

        self.layout = QVBoxLayout(self)
        self.progress_label = QLabel("Starting pipeline...", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.cancel_btn = QPushButton("Cancel Pipeline", self)

        self.layout.addWidget(self.progress_label)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.cancel_btn)

        self.cancel_requested = False

        self.session_manager, self.session = create_pipeline_session()
        self.worker = PipelineWorker(self.session_manager, self.session, self)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.cancel_btn.clicked.connect(self.cancel_pipeline)

        self.worker.start()

    def update_progress(self, stage: str, progress: float):
        self.progress_label.setText(f"{stage}: {progress:.2f}%")
        self.progress_bar.setValue(int(progress))

    def on_finished(self):
        if self.cancel_requested:
            self.close()
        else:
            self.progress_label.setText("Pipeline finished!")
            self.cancel_btn.setEnabled(False)

    def on_error(self, err: str):
        self.progress_label.setText(f"Error: {err}")
        if self.cancel_requested:
            self.close()

    def cancel_pipeline(self):
        if not self.cancel_requested:
            self.cancel_requested = True
            self.worker.cancel()
            self.progress_label.setText("Cancelling pipeline...")
            self.cancel_btn.setEnabled(False)


class MainWindow(QWidget):
    """
    Main window that displays a single 'Start' button to launch the pipeline dialog.
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
        dialog = PipelineDialog(self)
        dialog.exec()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
