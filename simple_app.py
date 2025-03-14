import sys
import mediapipe as mp
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QStatusBar
from pathlib import Path


from src.models.session import Session
from src.models.session_files import SessionFiles
from src.ui.workers.process_session_worker import ProcessSessionWorker
from src.ui.workers.annotate_video_worker import AnnotateVideoWorker
from src.config import DATA_DIR, SESSIONS_DIR
from src.ui.workers.process_landmarks_worker import ProcessLandmarksWorker
from src.ui.workers.session_operations import CreateSessionWorker


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

    def pipeline_finished(self):
        self.show_message("Pipeline finished")

    def pipeline_cancelled(self):
        self.show_message("Pipeline canceled")

    def worker_error(self, error_message: str):
        self.show_message(f"Error: {error_message}")

    def reset(self):
        self.show_message("Ready")


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
        self.worker = None

        # Variables
        self.session: Session | None = None
        self.landmark_data: LandmarkData | None = None

    def start_pipeline(self):
        session_title = "test_session"
        original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
        sessions_directory = SESSIONS_DIR


        self.worker = CreateSessionWorker(
            session_title=session_title,
            original_video_path=original_video_path,
            sessions_directory=sessions_directory,
            overwrite=True
        )
        self.worker.started.connect(self.worker_started)
        self.worker.error.connect(self.worker_error)
        self.worker.canceled.connect(self.worker_cancelled)
        self.worker.status.connect(self.update_status)
        self.worker.result.connect(self.worker_result)
        self.worker.finished.connect(self.worker_finished)
        self.start_worker()

    def update_status(self, message: str = "Message", progress: int | float | None = None):
        self.status_manager.update_progress(message, progress)

    def worker_started(self):
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def worker_finished(self):
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def worker_cancelled(self):
        self.status_manager.show_message("Pipeline canceled", 1000)

    def worker_error(self, error_message):
        self.status_manager.show_message(f"Error: {error_message}", 1000)

    def worker_result(self, result):
        self.status_manager.show_message("Session created successfully.", 1000)
        print(result)

    def start_worker(self):
        self.worker.run()

    def cancel_worker(self):
        self.worker.cancel()


# --- Main Application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
