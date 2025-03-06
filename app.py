import sys
import mediapipe as mp
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QStatusBar
from pathlib import Path


from src.models.annotation_preferences import AnnotationPreferences
from src.models.landmark_data import LandmarkData
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session import Session
from src.ui.workers.create_session_worker import CreateSessionWorker
from src.ui.workers.clone_cfr_video_worker import CloneCFRVideoWorker
from src.ui.workers.annotate_video_worker import AnnotateVideoWorker

from src.config import DATA_DIR
from src.ui.workers.process_landmarks_worker import ProcessLandmarksWorker


# --- MainWindow Implementation ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Worker Thread Example")
        self.resize(400, 200)

        # Create a status bar and disable the size grip.
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Create a central widget and layout.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Button to start the current_worker thread.
        self.start_button = QPushButton("Start Worker")
        self.start_button.clicked.connect(self.create_session)
        layout.addWidget(self.start_button)

        # Button to cancel the current_worker thread.
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_worker)
        self.cancel_button.setEnabled(False)  # Initially disabled.
        layout.addWidget(self.cancel_button)

        # Reference to the current_worker thread.
        self.current_worker = None

        # Variables
        self.session: Session | None = None
        self.landmark_data: LandmarkData | None = None

    def create_session(self):
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_bar.showMessage("Pipeline started")

        # Provide dummy parameters for the current_worker.
        session_title = "test_session"
        original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
        mediapipe_preferences = MediapipePreferences()
        annotation_preferences = AnnotationPreferences()

        self.current_worker = CreateSessionWorker(
            session_title,
            original_video_path,
            mediapipe_preferences,
            annotation_preferences,
            overwrite=True
        )
        self.current_worker.progress.connect(self.update_progress)
        self.current_worker.canceled.connect(self.pipeline_cancelled)
        self.current_worker.error_occurred.connect(self.worker_error)
        self.current_worker.finished.connect(self.clone_cfr_video)
        self.current_worker.start()

    def clone_cfr_video(self):
        self.session = self.current_worker.session
        print("got to here")
        # Define a new current_worker
        self.current_worker = CloneCFRVideoWorker(
            input_video_path=self.session.original_video_path,
            output_video_path=self.session.files.raw_video,
        )
        self.current_worker.progress.connect(self.update_progress)
        self.current_worker.canceled.connect(self.pipeline_cancelled)
        self.current_worker.error_occurred.connect(self.worker_error)
        self.current_worker.finished.connect(self.process_landmarks)
        self.current_worker.start()

    def process_landmarks(self):
        self.session.video_metadata = self.current_worker.video_metadata
        print(self.session.video_metadata)
        self.current_worker = ProcessLandmarksWorker(
            raw_video_path=self.session.files.raw_video,
            video_metadata=self.session.video_metadata,
            landmark_data_path=self.session.files.landmark_data,
            mediapipe_preferences=self.session.mediapipe_preferences
        )
        self.current_worker.progress.connect(self.update_progress)
        self.current_worker.canceled.connect(self.pipeline_cancelled)
        self.current_worker.error_occurred.connect(self.worker_error)
        self.current_worker.finished.connect(self.annotate_video)
        self.current_worker.start()

    def annotate_video(self):
        self.landmark_data = self.current_worker.landmark_data
        self.current_worker = AnnotateVideoWorker(
            raw_video_path=self.session.files.raw_video,
            annotated_video_path=self.session.files.annotated_video,
            video_metadata=self.session.video_metadata,
            landmark_data=self.landmark_data,
            annotation_preferences=self.session.annotation_preferences
        )
        self.current_worker.progress.connect(self.update_progress)
        self.current_worker.canceled.connect(self.pipeline_cancelled)
        self.current_worker.error_occurred.connect(self.worker_error)
        self.current_worker.finished.connect(self.finished_pipeline)
        self.current_worker.start()

    def cancel_worker(self):
        if self.current_worker is not None:
            self.current_worker.cancel()
            self.cancel_button.setEnabled(False)

    def update_progress(self, message, progress):
        self.status_bar.showMessage(f"{message}: {progress}%")

    def finished_pipeline(self):
        self.status_bar.showMessage("Pipeline finished")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def pipeline_cancelled(self):
        self.status_bar.showMessage("Pipeline canceled")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def worker_error(self, error_message):
        self.status_bar.showMessage(f"Error: {error_message}")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

# --- Main Application ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
