import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from src.ui.pages.home_page import HomePage
from src.ui.pages.session_page import SessionPage
from src.config import logger
from src.session import Session


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My PyQt6 App")
        self.setGeometry(100, 100, 800, 600)

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

    def load_session(self, selected_session_folder: Path):
        """Loads a session and switches to the session page."""
        try:
            selected_session_folder = Path(selected_session_folder)

            logger.info(f"attempting to load selected session from {selected_session_folder}")

            # Check if folder exists
            if not selected_session_folder.exists():
                logger.error(f"Session folder does not exist: {selected_session_folder}")
                return

            logger.info("Calling Session.load()")

            try:
                current_session = Session.load(selected_session_folder)
            except Exception as e:
                logger.error(f"Failed to load session: {e}")
                return

            logger.info("Session loaded successfully")

            valid, msg = current_session.is_valid_to_view()
            if not valid:
                logger.error(msg)
                return

            video_path = current_session.annotated_video_path
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

        except Exception as e:
            logger.error(f"Unexpected error in load_session: {e}")
            raise

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