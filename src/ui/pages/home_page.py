# src/pages/home_page.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt6.QtCore import QDir
from src.config import SESSIONS_DIR


class HomePage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title Label
        title_label = QLabel("Rowing Session Analyzer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        # Create New Session Button (Currently non-functional)
        btn_create_session = QPushButton("Create New Session")
        layout.addWidget(btn_create_session)

        # Open Existing Session Button
        btn_open_session = QPushButton("Open Existing Session")
        btn_open_session.clicked.connect(self.open_existing_session)
        layout.addWidget(btn_open_session)

    def open_existing_session(self):
        """Opens a file dialog to select a session folder and loads the session."""
        session_folder = QFileDialog.getExistingDirectory(
            self,
            "Select a Session Folder",
            str(SESSIONS_DIR),
            QFileDialog.Option.ShowDirsOnly
        )

        self.main_app.load_session(session_folder)
