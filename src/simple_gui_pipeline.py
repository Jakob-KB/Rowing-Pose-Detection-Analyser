# src/simple_gui_pipeline.py

import sys
from pathlib import Path

import mediapipe as mp
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QProgressBar
)

from src.config import DATA_DIR
from src.modules.session_manager import SessionManager
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.annotate_video import AnnotateVideo


class WorkerThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress_update = pyqtSignal(str, float)  # Signal to update progress (stage, progress%)

    def __init__(self, session_title: str, input_video_path: str, parent=None):
        super().__init__(parent)
        self.session_title = session_title
        self.input_video_path = input_video_path

    def run(self):
        # Define a progress callback that emits our custom signal.
        def gui_progress_callback(stage: str, progress: float) -> None:
            self.progress_update.emit(stage, progress)

        try:
            session_title = self.session_title
            input_video_path = Path(self.input_video_path)

            print(f"Creating session: {session_title}")
            print(f"Input video path: {input_video_path}")

            # Create a new session
            session_manager = SessionManager()
            session = session_manager.new_session(
                session_title=session_title,
                original_video_path=input_video_path,
                progress_callback=gui_progress_callback,
                overwrite=True
            )

            # Process landmarks and annotate video
            processor = ProcessLandmarks()
            landmark_data = processor.run(
                raw_video_path=session.files.raw_video,
                video_metadata=session.video_metadata,
                mediapipe_preferences=session.mediapipe_preferences,
                progress_callback=gui_progress_callback
            )
            session_manager.save_landmarks_to_session(session, landmark_data)
            annotator = AnnotateVideo()
            annotator.run(
                raw_video_path=session.files.raw_video,
                annotated_video_path=session.files.annotated_video,
                video_metadata=session.video_metadata,
                landmark_data=landmark_data,
                annotation_preferences=session.annotation_preferences,
                progress_callback=gui_progress_callback
            )

            print("Main function completed.")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class SimpleMainPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Process Session")
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Session Title Input
        title_layout = QHBoxLayout()
        title_label = QLabel("Session Title:")
        self.title_edit = QLineEdit()
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # Input Video File Selector
        video_layout = QHBoxLayout()
        video_label = QLabel("Input Video:")
        self.video_edit = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_video)
        video_layout.addWidget(video_label)
        video_layout.addWidget(self.video_edit)
        video_layout.addWidget(browse_button)
        layout.addLayout(video_layout)

        # Process Session Button (store reference for disabling/enabling)
        self.process_button = QPushButton("Process Session")
        self.process_button.clicked.connect(self.process_session)
        layout.addWidget(self.process_button)

        # Progress Label & Progress Bar for UI feedback
        self.progress_label = QLabel("Progress: 0%")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def browse_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            str(Path(DATA_DIR / "videos")),
            "Video Files (*.mp4 *.avi *.mov)"
        )
        if file_name:
            self.video_edit.setText(file_name)

    def process_session(self):
        session_title = self.title_edit.text().strip()
        input_video_path = self.video_edit.text().strip()

        if not session_title:
            print("Please enter a session title.")
            return
        if not input_video_path:
            print("Please select an input video file.")
            return

        # Disable the process button during processing
        self.process_button.setEnabled(False)
        # Reset progress bar and label
        self.progress_bar.setValue(0)
        self.progress_label.setText("Progress: 0%")

        self.worker = WorkerThread(session_title, input_video_path)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.start()

    def update_progress(self, stage: str, progress: float):
        # Update UI elements with the latest progress data
        self.progress_label.setText(f"{stage}: {progress:.2f}% completed")
        self.progress_bar.setValue(int(progress))

    def on_finished(self):
        print("Workflow finished successfully.")
        self.process_button.setEnabled(True)

    def on_error(self, error_message):
        print(f"Workflow error: {error_message}")
        self.process_button.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleMainPage()
    window.show()
    sys.exit(app.exec())
