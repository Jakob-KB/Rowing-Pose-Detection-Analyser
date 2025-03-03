# src/ui/components/loading_dialog.py

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton

class LoadingDialog(QDialog):
    def __init__(self, pipeline_worker, parent=None):
        super().__init__(parent)
        # Disable the close ("X") button.
        flags = self.windowFlags()
        flags &= ~Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)

        self.pipeline_worker = pipeline_worker

        self.setWindowTitle("Pipeline Progress")
        self.setFixedSize(400, 200)

        self.layout = QVBoxLayout(self)

        self.progress_label = QLabel("Starting pipeline...", self)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.layout.addWidget(self.progress_bar)

        self.cancel_btn = QPushButton("Cancel Pipeline", self)
        self.layout.addWidget(self.cancel_btn)

        self.cancel_btn.clicked.connect(self.cancel_pipeline)

        # Connect pipeline signals to dialog methods.
        self.pipeline_worker.progress_update.connect(self.update_progress)
        self.pipeline_worker.finished.connect(self.on_finished)
        self.pipeline_worker.error.connect(self.on_error)

        # Start the pipeline.
        self.pipeline_worker.start()

    def update_progress(self, stage: str, progress: float):
        self.progress_label.setText(f"{stage}: {progress:.2f}%")
        self.progress_bar.setValue(int(progress))

    def on_finished(self):
        if self.pipeline_worker.token.cancelled:
            self.reject()
        else:
            self.accept()

    def on_error(self, err: str):
        self.progress_label.setText(f"Error: {err}")
        self.cancel_btn.setEnabled(False)
        self.reject()

    def cancel_pipeline(self):
        if not self.pipeline_worker.token.cancelled:
            self.pipeline_worker.cancel()
            self.progress_label.setText("Cancelling pipeline...")
            self.cancel_btn.setEnabled(False)
