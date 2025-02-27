import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QStyle
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTimer
from src.config import SESSIONS_DIR


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        """Allow clicking anywhere on the slider to seek to that position."""
        if event.button() == Qt.MouseButton.LeftButton:
            new_position = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), int(event.position().toPoint().x()), self.width()
            )
            self.setValue(new_position)  # Move the slider to the clicked position
            self.sliderMoved.emit(new_position)  # Emit the sliderMoved signal
        super().mousePressEvent(event)  # Ensure dragging still works


class VideoPlayer(QWidget):
    def __init__(self, video_path_str, metrics=None, fps=30.0):
        super().__init__()
        self.setWindowTitle("Rowing Video Player")

        # Store metrics & fps if needed
        self.metrics = metrics if metrics else []
        self.fps = fps

        # Setup MediaPlayer and Audio
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Video widget
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        # Load the video
        self.player.setSource(QUrl.fromLocalFile(str(video_path_str)))

        # Create the layout (vertical: video on top, controls on bottom)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Add the video widget to the top
        main_layout.addWidget(self.video_widget)

        # --- CONTROLS ROW BELOW THE VIDEO ---
        controls_layout = QHBoxLayout()

        # 1. Play/Pause Toggle Button (Shorter width)
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.setFixedWidth(50)  # Set smaller width
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.play_pause_btn)

        # 2. Speed Buttons (Shorter width)
        self.speed05_btn = QPushButton("0.5x")
        self.speed05_btn.setFixedWidth(50)
        self.speed05_btn.clicked.connect(lambda: self.set_speed(0.5))
        controls_layout.addWidget(self.speed05_btn)

        self.speed1_btn = QPushButton("1x")
        self.speed1_btn.setFixedWidth(50)
        self.speed1_btn.clicked.connect(lambda: self.set_speed(1.0))
        controls_layout.addWidget(self.speed1_btn)

        self.speed2_btn = QPushButton("2x")
        self.speed2_btn.setFixedWidth(50)
        self.speed2_btn.clicked.connect(lambda: self.set_speed(2.0))
        controls_layout.addWidget(self.speed2_btn)

        # 3. Clickable and Draggable Slider (seek bar)
        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)  # We will set the actual range once the media is loaded
        self.slider.sliderMoved.connect(self.seek_to_position)
        controls_layout.addWidget(self.slider, 1)  # '1' to let the slider expand in the layout

        main_layout.addLayout(controls_layout)

        # Connect signals from the player for slider synchronization
        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.update_slider_range)

        # Loop the video when it finishes
        self.player.mediaStatusChanged.connect(self.handle_media_status)

        # Setup a timer for updating any frame-based metrics (if you want time-based polling)
        self.timer = QTimer(self)
        self.timer.setInterval(50)  # 20 polls/sec
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start()

    # --- Control Handlers ---
    def toggle_play_pause(self):
        """Toggles play/pause based on the player's current state."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_pause_btn.setText("Play")
        else:
            self.player.play()
            self.play_pause_btn.setText("Pause")

    def set_speed(self, rate: float):
        """Sets the playback speed (rate). 1.0 is normal."""
        self.player.setPlaybackRate(rate)

    # --- Slider / Seeking ---
    def update_slider_position(self, position_ms: int):
        """Called when the player updates its position. We move the slider accordingly."""
        self.slider.blockSignals(True)  # prevent recursion when we set the slider value
        self.slider.setValue(position_ms)
        self.slider.blockSignals(False)

    def update_slider_range(self, duration_ms: int):
        """Called when the media's duration is known. Sets the slider's maximum."""
        self.slider.setRange(0, duration_ms)

    def seek_to_position(self, position_ms: int):
        """Called when the user moves the slider or clicks on the slider bar. We seek the player to that position."""
        self.player.setPosition(position_ms)

    # --- Video Looping ---
    def handle_media_status(self, status):
        """Restart the video when it reaches the end."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)  # Restart the video
            self.player.play()

    # --- Frame-based Metric Polling (Optional) ---
    def update_metrics(self):
        """Poll the current playback time (ms), convert to frame index, get metrics."""
        position_ms = self.player.position()  # current time in ms
        current_time_s = position_ms / 1000.0
        current_frame = int(current_time_s * self.fps)

        # If you have a metrics array or dict, fetch and display
        # Example:
        # if 0 <= current_frame < len(self.metrics):
        #     metric_value = self.metrics[current_frame]
        #     # Update a label, chart, etc.
        # else:
        #     pass
        # In this example, we simply do nothing


def main():
    app = QApplication(sys.argv)

    # Example: load precomputed metrics into a list
    # For demonstration, let's say we have 10,000 frames, each with a simple integer metric
    metrics = list(range(10000))

    video_path = SESSIONS_DIR / "athlete_1" / "annotated.mp4"
    window = VideoPlayer(video_path, metrics, fps=30.0)
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
