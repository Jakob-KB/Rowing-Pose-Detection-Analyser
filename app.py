import sys
import mediapipe as mp
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QStatusBar
from pathlib import Path

from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session import Session
from src.models.session_files import SessionFiles
from src.ui.workers.process_session_worker import ProcessSessionWorker
from src.ui.workers.annotate_video_worker import AnnotateVideoWorker
from src.config import DATA_DIR, SESSIONS_DIR
from src.ui.workers.process_landmarks_worker import ProcessLandmarksWorker


def exception_hook(exctype, value, traceback):
    # Print error to CLI
    print("Unhandled exception:", value, file=sys.stderr)
    # Optionally, you can call the default excepthook if desired.
    sys.__excepthook__(exctype, value, traceback)


# Set exception hook
sys.excepthook = exception_hook


class StatusBarManager:
    def __init__(self, status_bar: QStatusBar):
        self.status_bar = status_bar

    def show_message(self, message: str, timeout: int = 0):
        self.status_bar.showMessage(message, timeout)

    def update_progress(self, message: str, progress: int | float | None = None):
        if progress is None:
            self.show_message(message)
        else:
            self.show_message(f"{message}: {progress}%")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Worker Thread Example")
        self.resize(400, 200)

        # Create and set up the status bar.
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_manager = StatusBarManager(self.status_bar)
        self.status_manager.reset()

        # Create a central widget and layout.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Button to start the worker thread.
        self.start_button = QPushButton("Start Worker")
        self.start_button.clicked.connect(self.start_pipeline)
        layout.addWidget(self.start_button)

        # Button to cancel the worker thread.
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_worker)
        self.cancel_button.setEnabled(False)  # Initially disabled.
        layout.addWidget(self.cancel_button)

        # Reference to the current worker thread.
        self.current_worker = None

        # Variables
        self.session: Session | None = None
        self.landmark_data: LandmarkData | None = None

    def start_pipeline(self):
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_manager.show_message("Pipeline started")

        # Dummy parameters for the worker.
        session_title = "test_session"
        original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
        session_directory = SESSIONS_DIR / session_title
        mediapipe_preferences = MediapipePreferences()
        annotation_preferences = AnnotationPreferences()

        # Instantiate the Session model.
        self.session = Session(
            title=session_title,
            original_video_path=original_video_path,
            directory=session_directory,
            files=SessionFiles.from_session_directory(SESSIONS_DIR / session_title),
            video_metadata=None,
            mediapipe_preferences=mediapipe_preferences,
            annotation_preferences=annotation_preferences
        )

        self.current_worker = ProcessSessionWorker(
            session=self.session,
            overwrite=True
        )
        self.current_worker.progress.connect(self.update_progress)
        self.current_worker.canceled.connect(self.pipeline_cancelled)
        self.current_worker.error_occurred.connect(self.worker_error)
        self.current_worker.finished.connect(self.worker_finished)
        self.current_worker.start()


    def update_progress(self, message: str = "Message", progress: int | float | None = None):
        self.status_manager.update_progress(message, progress)

    def worker_finished(self):
        self.status_manager.show_message("Pipeline finished", 1)
        print('!!')
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def pipeline_cancelled(self):
        self.status_manager.pipeline_cancelled()
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def worker_error(self, error_message):
        self.status_manager.worker_error(error_message)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)


# --- Main Application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
