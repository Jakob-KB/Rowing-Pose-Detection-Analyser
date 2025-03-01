import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from src.ui.pages.home_page import HomePage
from src.ui.pages.session_page import SessionPage
from src.config import logger
from src.modules.session_manager import SessionManager
from src.models.session import Session

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My PyQt6 App")
        self.setGeometry(100, 100, 800, 600)

        # Initialize session manager
        self.session_manager = SessionManager()

        # Stack widget to manage multiple pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Initialize pages
        self.home_page = HomePage(self)
        self.session_page = None  # Will be initialized when a session is opened

        # Add Home Page to the stack
        self.stack.addWidget(self.home_page)

        # Show the home page initially
        self.stack.setCurrentWidget(self.home_page)

    def load_session(self, selected_session_dir: Path):
        selected_session_dir = Path(selected_session_dir)

        logger.info(f"attempting to load selected session from {selected_session_dir}")

        # Check if folder exists
        if not selected_session_dir.exists():
            logger.error(f"Session folder does not exist: {selected_session_dir}")
            return

        session = self.session_manager.load_existing_session(selected_session_dir)

        logger.info("Session loaded successfully")

        video_path = session.files.annotated_video
        logger.info(f"Annotated video path: {video_path}")

        if not video_path.exists():
            logger.error("Annotated video does not exist.")
            return

        # Log before switching pages
        logger.info("Switching to session page")

        if self.session_page:
            self.stack.removeWidget(self.session_page)

        self.session_page = SessionPage(self, video_path)
        logger.info("SessionPage initialized")

        self.stack.addWidget(self.session_page)
        self.stack.setCurrentWidget(self.session_page)

        logger.info("Successfully switched to session page")


    def switch_page(self, page):
        """Switches to the given page."""
        self.stack.setCurrentWidget(page)


def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()