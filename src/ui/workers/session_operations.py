import re
import shutil
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from src.config import cfg, logger
from src.models.session import Session
from src.models.annotation_preferences import AnnotationPreferences
from src.models.mediapipe_preferences import MediapipePreferences
from src.models.session_files import SessionFiles

TITLE_REGEX = re.compile(r'^[A-Za-z0-9_-]+$')
FINAL_MESSAGE_TIMEOUT_TIME = 3000

class CreateSessionWorker(QObject):
    """
    Worker class responsible for creating a new session.
    """
    started = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str, object)
    finished = pyqtSignal()
    result = pyqtSignal(object)

    def __init__(
        self,
        session_title: str,
        sessions_directory: Path,
        original_video_path: Path,
        overwrite: bool = False,
        parent: QObject = None
    ) -> None:
        super().__init__(parent)
        self.session_title = session_title
        self.sessions_directory = sessions_directory
        self.original_video_path = original_video_path
        self.overwrite = overwrite
        self._is_canceled = False

    @pyqtSlot()
    def run(self):
        self.started.emit()
        try:
            self.validate_session_title()
            session_dir = self.check_existing_session()
            session = self.create_session_object(session_dir)
            self.setup_session_directory(session)
            self.save_session_config(session)
            self.result.emit(session)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def validate_session_title(self) -> None:
        self.update_state("Checking session title validity")
        if not TITLE_REGEX.fullmatch(self.session_title):
            raise ValueError("Invalid session title contains invalid characters.")
        self.check_cancelled()

    def check_existing_session(self) -> Path:
        self.update_state("Checking if session already exists.")
        session_dir = self.sessions_directory / self.session_title
        if session_dir.exists():
            if self.overwrite:
                self.update_state("Attempting to overwrite existing session.")
                expected_files = {
                    cfg.session.files.session_config,
                    cfg.session.files.raw_video,
                    cfg.session.files.landmark_data,
                    cfg.session.files.analysis_data,
                    cfg.session.files.annotated_video,
                }
                existing_files = {file.name for file in session_dir.iterdir()}
                if not existing_files.issubset(expected_files):
                    raise FileExistsError("Foreign files found. Cannot override, delete existing manually.")
                shutil.rmtree(session_dir)
            else:
                raise FileExistsError("Session already exists.")
        self.check_cancelled()
        return session_dir

    def create_session_object(self, session_dir: Path) -> Session:
        self.update_state("Creating new session object")
        mediapipe_prefs = MediapipePreferences()
        annotation_prefs = AnnotationPreferences()
        session = Session(
            title=self.session_title,
            original_video_path=self.original_video_path,
            directory=session_dir,
            files=SessionFiles.from_session_directory(session_dir),
            video_metadata=None,
            mediapipe_preferences=mediapipe_prefs,
            annotation_preferences=annotation_prefs
        )
        self.check_cancelled()
        return session

    def setup_session_directory(self, session: Session) -> None:
        self.update_state("Setting up session directory")
        session.directory.mkdir(parents=True, exist_ok=False)
        self.check_cancelled()

    def save_session_config(self, session: Session) -> None:
        self.update_state("Saving session config")
        with open(session.files.session_config, "w") as f:
            f.write(session.model_dump_json(indent=4))
        self.check_cancelled()

    @pyqtSlot()
    def cancel(self):
        """Slot to trigger cancellation of the operation."""
        self._is_canceled = True

    def check_cancelled(self) -> None:
        if self._is_canceled:
            self.status.emit("Cancelled session creation.", None, FINAL_MESSAGE_TIMEOUT_TIME)
            raise Exception("Operation cancelled.")

    def update_state(self, message: str, progress_value: int | None = None) -> None:
        """Helper method to emit progress updates."""
        if progress_value is not None:
            self.status.emit(message, progress_value)
        else:
            self.status.emit(message, None)
