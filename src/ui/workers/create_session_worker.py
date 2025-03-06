import shutil
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from src.models.annotation_preferences import AnnotationPreferences
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session import Session
from src.models.session_files import SessionFiles
from src.config import SESSIONS_DIR, logger

class CreateSessionWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        session_title: str,
        original_video_path: Path,
        mediapipe_preferences: MediapipePreferences,
        annotation_preferences: AnnotationPreferences,
        overwrite: bool = False,
        parent=None
    ) -> None:
        super().__init__(parent)
        self.session_title: str = session_title
        self.original_video_path: Path = original_video_path
        self.mediapipe_preferences: MediapipePreferences = mediapipe_preferences
        self.annotation_preferences: AnnotationPreferences = annotation_preferences
        self.overwrite: bool = overwrite

        self.session: Session | None = None
        self._is_canceled: bool = False

    def cancel(self):
        """Signal the thread to cancel its work."""
        self._is_canceled = True

    def _cleanup(self):
        try:
            if self.session and self.session.directory.exists():
                shutil.rmtree(self.session.directory)
                logger.info(f"Session '{self.session_title}' cleaned up.")
        except Exception as e:
            logger.error(f"Error cleaning up session '{self.session_title}': {e}")

    def run(self):
        try:
            # Construct the session directory and files.
            session_directory = SESSIONS_DIR / self.session_title
            self.progress.emit("Validating session title", 0)

            # Create session files instance.
            files: SessionFiles = SessionFiles.from_session_directory(
                session_directory=session_directory
            )

            # Validate existing session directory.
            if session_directory.exists():
                if self.overwrite:
                    shutil.rmtree(session_directory)
                    self.progress.emit("Overwriting old session", 15)
                else:
                    raise FileExistsError(f"Session '{self.session_title}' already exists.")

            # Instantiate the Session model.
            self.session = Session(
                title=self.session_title,
                original_video_path=self.original_video_path,
                directory=session_directory,
                files=files,
                video_metadata=None,
                mediapipe_preferences=self.mediapipe_preferences,
                annotation_preferences=self.annotation_preferences
            )

            # Create the session directory.
            self.progress.emit("Creating session directory", 25)
            session_directory.mkdir(parents=True, exist_ok=False)
            if self._is_canceled:
                self._cleanup()
                self.canceled.emit()
                return

            # Save the session configuration.
            self.progress.emit("Saving session config", 35)
            with open(self.session.files.session_config, "w") as f:
                f.write(self.session.model_dump_json(indent=4))
            logger.info(f"Session created and saved to {self.session.directory}.")

            # Simulate further processing steps from 35% to 100%.
            total_steps = 50  # Determines how many steps the simulation takes.
            for step in range(total_steps):
                if self._is_canceled:
                    self._cleanup()
                    self.canceled.emit()
                    return
                # Compute progress from 35% to 100%.
                progress_percentage = 35 + int((step + 1) / total_steps * (100 - 35))
                self.progress.emit("Processing session", progress_percentage)
                self.msleep(5)  # Simulate work (adjust delay as needed)

            # When done, emit finished signal.
            self.finished.emit()

        except Exception as e:
            # Log and emit the error so that the main thread can handle it.
            error_msg = f"Error creating session: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
