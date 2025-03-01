# src/pages/create_session_page.py
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QSpacerItem, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt
from src.config import DATA_DIR


class CreateSessionPage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.selected_video_path = None

        # Main layout setup with margins and spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Back Button to return to the Home Page
        back_button = QPushButton("Back")
        back_button.setFixedWidth(100)
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Page Title
        title_label = QLabel("Create New Session")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
        """)
        layout.addWidget(title_label)

        # Session Title Input Section
        session_title_label = QLabel("Session Title:")
        self.session_title_input = QLineEdit()
        self.session_title_input.setPlaceholderText("Enter session title")
        layout.addWidget(session_title_label)
        layout.addWidget(self.session_title_input)

        # Video Upload Section
        video_upload_label = QLabel("Upload Original Video:")
        layout.addWidget(video_upload_label)

        # Horizontal layout for file path display and browse button
        video_upload_layout = QHBoxLayout()
        self.video_path_label = QLabel("No file selected")
        video_browse_button = QPushButton("Browse")
        video_browse_button.clicked.connect(self.browse_video)
        video_upload_layout.addWidget(self.video_path_label)
        video_upload_layout.addWidget(video_browse_button)
        layout.addLayout(video_upload_layout)

        # Create Session Button
        create_session_button = QPushButton("Create Session")
        create_session_button.setFixedWidth(150)
        create_session_button.clicked.connect(self.create_session)
        layout.addWidget(create_session_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Bottom spacer to balance the layout vertically
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def go_back(self):
        """Switches back to the Home Page."""
        self.main_app.switch_page(self.main_app.home_page)

    def browse_video(self):
        """Opens a file dialog for the user to select a video file."""
        default_video_path: Path = DATA_DIR / "videos"
        video_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            str(default_video_path),
            "Video Files (*.mp4 *.avi *.mov)"
        )
        if video_file:
            self.selected_video_path = video_file
            # Display only the file name
            self.video_path_label.setText(Path(video_file).name)

    def create_session(self):
        """Handles the creation of a new session after validating input."""
        session_title = self.session_title_input.text().strip()
        if not session_title:
            QMessageBox.warning(self, "Input Error", "Please enter a session title.")
            return
        if not self.selected_video_path:
            QMessageBox.warning(self, "Input Error", "Please select a video file.")
            return

        new_session = self.main_app.session_manager.new_session(session_title, self.selected_video_path)
        self.main_app.session_manager.set_active_session(new_session)

        print(self.main_app.session_manager.active_session.title)