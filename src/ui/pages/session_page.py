from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from src.ui.components.video_player import VideoPlayer

class SessionPage(QWidget):
    def __init__(self, main_app, video_path):
        super().__init__()
        self.main_app = main_app  # Reference to the main application for navigation
        self.setWindowTitle("Session Analysis")

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Video Player Component
        self.video_player = VideoPlayer(video_path)
        main_layout.addWidget(self.video_player)

        # Back to Home Button
        self.back_button = QPushButton("Back to Home")
        self.back_button.clicked.connect(lambda: self.main_app.switch_page(self.main_app.home_page))
        main_layout.addWidget(self.back_button)
