# app.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from src.ui.pages import HomePage
from src.ui.pages.session_page import SessionPage
from src.config import SESSIONS_DIR

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
        self.session_page = SessionPage(self, video_path=SESSIONS_DIR / "athlete_1" / "annotated.mp4")

        # Add pages to the stack
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.session_page)

        # Show the home page initially
        self.stack.setCurrentWidget(self.home_page)

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
