# src/ui/pages/session_page.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from src.ui.components.video_player import VideoPlayer


class SessionPage(QWidget):
    def __init__(self, app_context, navigate, parent=None):
        """
        app_context: Shared application context that holds the current session.
        navigate: Callback to switch pages.
        """
        super().__init__(parent)
        self.app_context = app_context
        self.navigate = navigate

        self.setWindowTitle("Session Page")
        self.setFixedSize(600, 400)

        main_layout = QVBoxLayout(self)

        # Retrieve the annotated video path from the current session.
        video_path = self.app_context.current_session.files.annotated_video

        if not video_path.exists():
            print("ERROR: Video path does not exist!")
            # Optionally, display an error message in the UI.
        else:
            self.video_player = VideoPlayer(video_path)
            main_layout.addWidget(self.video_player)

        self.back_button = QPushButton("Back to Home", self)
        self.back_button.clicked.connect(self.go_home)
        main_layout.addWidget(self.back_button)

    def go_home(self):
        from src.ui.pages.home_page import HomePage
        home_page = HomePage(app_context=self.app_context, navigate=self.navigate)
        self.navigate(home_page)
