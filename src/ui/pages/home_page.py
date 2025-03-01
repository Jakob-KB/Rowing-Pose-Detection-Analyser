# src/pages/home_page.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QDir, Qt
from PyQt6.QtGui import QPixmap
from pathlib import Path
from src.config import SESSIONS_DIR, SRC_DIR


class HomePage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        # Main layout with improved spacing and margins
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Title Label with centered alignment and enhanced styling
        title_label = QLabel("Rowing Session Analyzer")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffff;
            margin-bottom: 20px;
        """)
        layout.addWidget(title_label)

        # Logo Image: Place your logo above the buttons
        logo_path: Path = SRC_DIR / "assets" / "logo.png"
        logo_label = QLabel()
        logo_pixmap = QPixmap(str(logo_path))
        if logo_pixmap.isNull():
            print(f"Logo image not found at: {logo_path}")
        # Scale the logo to 400 pixels wide (2x the button width)
        logo_pixmap = logo_pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # Top spacer to push content toward the center (if desired)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Fixed width for both buttons
        fixed_width = 200

        # Create New Session Button with modern styling (currently non-functional)
        btn_create_session = QPushButton("Create New Session")
        btn_create_session.setFixedWidth(fixed_width)
        btn_create_session.setStyleSheet("""
            font-size: 16px;
            padding: 12px;
            border-radius: 8px;
            background-color: #4CAF50;
            color: white;
        """)
        layout.addWidget(btn_create_session, alignment=Qt.AlignmentFlag.AlignCenter)

        # Open Existing Session Button with similar styling
        btn_open_session = QPushButton("Open Existing Session")
        btn_open_session.setFixedWidth(fixed_width)
        btn_open_session.setStyleSheet("""
            font-size: 16px;
            padding: 12px;
            border-radius: 8px;
            background-color: #2196F3;
            color: white;
        """)
        btn_open_session.clicked.connect(self.open_existing_session)
        layout.addWidget(btn_open_session, alignment=Qt.AlignmentFlag.AlignCenter)

        # Bottom spacer for balanced vertical alignment
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def open_existing_session(self):
        """Opens a file dialog to select a session folder and loads the session."""
        session_folder = QFileDialog.getExistingDirectory(
            self,
            "Select a Session Folder",
            str(SESSIONS_DIR),
            QFileDialog.Option.ShowDirsOnly
        )
        if session_folder:  # Check if a folder was selected
            self.main_app.load_session(session_folder)
