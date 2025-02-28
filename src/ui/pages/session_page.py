from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from src.ui.components.video_player import VideoPlayer

class SessionPage(QWidget):
    def __init__(self, main_app, video_path):
        super().__init__()
        self.main_app = main_app  # Reference to MainApp for navigation

        print("Initializing SessionPage...")

        # Ensure video path exists
        if not video_path.exists():
            print("ERROR: Video path does not exist!")
            return

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Video Player Component
        self.video_player = VideoPlayer(video_path)
        print("VideoPlayer initialized")
        main_layout.addWidget(self.video_player)

        # Back to Home Button
        self.back_button = QPushButton("Back to Home")
        self.back_button.clicked.connect(lambda: self.main_app.switch_page(self.main_app.home_page))
        main_layout.addWidget(self.back_button)

        print("SessionPage initialization complete")
