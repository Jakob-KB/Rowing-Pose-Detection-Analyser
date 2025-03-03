# app.py

import sys
import shutil
import traceback

import mediapipe as mp
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from src.config import DATA_DIR, logger
from src.modules.session_manager import SessionManager
from src.modules.data_io import DataIO
from src.ui.pages.home_page import HomePage


class AppContext:
    """
    Holds global objects and state shared by the application.
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.data_io = DataIO()
        self.current_session = self.create_session()

    def create_session(self):
        session_title = "sample_session_v0"
        original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
        session = self.session_manager.create_session(
            session_title=session_title,
            original_video_path=original_video_path
        )
        # Delete existing session directory if it exists.
        if session.directory.exists():
            shutil.rmtree(session.directory)
        return session


class MainWindow(QMainWindow):
    def __init__(self, app_context: AppContext):
        super().__init__()
        self.setWindowTitle("My PyQt App")
        self.app_context = app_context

        # Create a QStackedWidget to handle navigation.
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        # Create and add the home page.
        self.home_page = HomePage(app_context=self.app_context, navigate=self.switch_page)
        self.stack.addWidget(self.home_page)

        # Initialize status bar for error messages.
        self.statusBar().showMessage("")

    def switch_page(self, page_widget):
        """
        Add the given page widget to the stack (if not already added) and switch to it.
        """
        if self.stack.indexOf(page_widget) == -1:
            self.stack.addWidget(page_widget)
        self.stack.setCurrentWidget(page_widget)

    def show_error(self, message: str, timeout: int = 0):
        """
        Show an error message in the status bar.
        timeout: milliseconds to show the message (0 means persistent).
        """
        self.statusBar().showMessage(message, timeout)


def global_exception_hook(exctype, value, tb):
    """
    Global exception hook to catch unhandled exceptions and display them.
    """
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("Unhandled exception:", err_msg)
    if hasattr(sys, "main_window") and sys.main_window is not None:
        sys.main_window.show_error("Error: " + str(value), timeout=0)
    logger.error(err_msg)
    sys.__excepthook__(exctype, value, tb)


def main():
    app = QApplication(sys.argv)
    app_context = AppContext()
    window = MainWindow(app_context)

    # Store the window as a global reference for the exception hook.
    sys.main_window = window

    # Install the global exception hook.
    sys.excepthook = global_exception_hook
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
