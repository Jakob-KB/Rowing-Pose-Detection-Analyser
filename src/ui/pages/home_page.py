# src/ui/pages/home_page.py

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QDialog
from src.config import SESSIONS_DIR, logger

class HomePage(QWidget):
    def __init__(self, app_context, navigate, parent=None):
        """
        app_context: Shared application context.
        navigate: A callback for page switching.
        """
        super().__init__(parent)
        self.app_context = app_context
        self.navigate = navigate

        self.setWindowTitle("Simple Pipeline")
        self.setFixedSize(400, 400)

        layout = QVBoxLayout(self)

        header = QLabel("Welcome to the Simple Pipeline", self)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.start_btn = QPushButton("Start", self)
        layout.addStretch(1)
        layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        self.start_btn.clicked.connect(self.create_session)

        # Button to load an existing session.
        self.load_session_btn = QPushButton("Load Existing Session", self)
        layout.addWidget(self.load_session_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.load_session_btn.clicked.connect(self.load_existing_session)

    def create_session(self):
        """
        Launches the generic loading dialog with the session creation pipeline.
        On success, navigates to the session page.
        """
        from src.ui.pipelines.create_session_pipeline import CreateSessionPipeline
        from src.ui.components.loading_dialog import LoadingDialog
        from PyQt6.QtWidgets import QDialog

        pipeline_worker = CreateSessionPipeline(app_context=self.app_context, parent=self)
        dialog = LoadingDialog(pipeline_worker=pipeline_worker, parent=self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            from src.ui.pages.session_page import SessionPage
            session_page = SessionPage(app_context=self.app_context, navigate=self.navigate)
            self.navigate(session_page)
        else:
            logger.info("Pipeline cancelled or failed; staying on home page.")

    def load_existing_session(self):
        """
        Opens a folder selection dialog for loading an existing session.
        The selected folder is displayed in the main window's status bar.
        """
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Session Folder",
            str(SESSIONS_DIR),
            QFileDialog.Option.ShowDirsOnly
        )

        from src.ui.pipelines.load_session_pipeline import LoadSessionPipeline
        from src.ui.components.loading_dialog import LoadingDialog
        from PyQt6.QtWidgets import QDialog

        pipeline_worker = LoadSessionPipeline(
            session_directory=Path(folder),
            app_context=self.app_context,
            parent=self
        )
        dialog = LoadingDialog(pipeline_worker=pipeline_worker, parent=self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            from src.ui.pages.session_page import SessionPage
            session_page = SessionPage(app_context=self.app_context, navigate=self.navigate)
            self.navigate(session_page)
        else:
            logger.info("Pipeline cancelled or failed; staying on home page.")
