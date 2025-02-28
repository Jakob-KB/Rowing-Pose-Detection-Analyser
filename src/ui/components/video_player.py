from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QStyle
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTimer


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
    def __init__(self, video_path, fps=30.0):
        super().__init__()

        self.fps = fps

        # Setup MediaPlayer and Audio
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Video widget
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        # Load the video
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))

        # Create the layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Add the video widget to the top
        main_layout.addWidget(self.video_widget)

        # --- CONTROLS ROW BELOW THE VIDEO ---
        controls_layout = QHBoxLayout()

        # 1. Play/Pause Toggle Button
        self.play_pause_btn = QPushButton("Pause")  # Start as "Pause" since video auto-plays
        self.play_pause_btn.setFixedWidth(50)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.play_pause_btn)

        # 2. Speed Buttons
        self.speed05_btn = QPushButton("0.5x")
        self.speed05_btn.setFixedWidth(35)
        self.speed05_btn.clicked.connect(lambda: self.set_speed(0.5))
        controls_layout.addWidget(self.speed05_btn)

        self.speed1_btn = QPushButton("1x")
        self.speed1_btn.setFixedWidth(35)
        self.speed1_btn.clicked.connect(lambda: self.set_speed(1.0))
        controls_layout.addWidget(self.speed1_btn)

        self.speed2_btn = QPushButton("2x")
        self.speed2_btn.setFixedWidth(35)
        self.speed2_btn.clicked.connect(lambda: self.set_speed(2.0))
        controls_layout.addWidget(self.speed2_btn)

        # 3. Clickable and Draggable Slider (seek bar)
        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.seek_to_position)
        controls_layout.addWidget(self.slider, 1)

        main_layout.addLayout(controls_layout)

        # Connect signals from the player for slider synchronization
        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.update_slider_range)

        # Loop the video when it finishes (without black flash)
        self.player.mediaStatusChanged.connect(self.handle_media_status)

        # Ensure the video always starts at the beginning
        self.player.setPosition(0)
        self.player.play()

    # --- Ensure Video Always Starts from Beginning ---
    def showEvent(self, event):
        """Ensure the video always starts from the beginning when this page is shown."""
        self.player.setPosition(0)
        self.player.play()
        self.play_pause_btn.setText("Pause")
        super().showEvent(event)

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
        """Sets the playback speed."""
        self.player.setPlaybackRate(rate)

    # --- Slider / Seeking ---
    def update_slider_position(self, position_ms: int):
        """Called when the player updates its position."""
        self.slider.blockSignals(True)
        self.slider.setValue(position_ms)
        self.slider.blockSignals(False)

        # Smooth looping: restart before reaching the last frame
        if self.player.duration() > 0 and position_ms >= self.player.duration() - 50:
            self.player.setPosition(1)

    def update_slider_range(self, duration_ms: int):
        """Called when the media's duration is known."""
        self.slider.setRange(0, duration_ms)

    def seek_to_position(self, position_ms: int):
        """Seeks to the selected video position."""
        self.player.setPosition(position_ms)

    # --- Video Looping (No Black Flash) ---
    def handle_media_status(self, status):
        """Smoothly restart the video when it reaches the end (no black flash)."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPlaybackRate(1.0)
            self.player.setPosition(1)
            self.player.play()
