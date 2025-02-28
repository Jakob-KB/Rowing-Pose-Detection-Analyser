# src/pages/home_page.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel

class HomePage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app  # Reference to MainApp for navigation

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
        btn_open_session.clicked.connect(lambda: self.main_app.switch_page(self.main_app.session_page))
        layout.addWidget(btn_open_session)
