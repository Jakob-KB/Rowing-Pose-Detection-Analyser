import datetime
import time
import tkinter as tk
from tkintervideoplayer import TkinterVideo
from src.config import DATA_DIR


def format_time(seconds: float) -> str:
    """Formats seconds into MM:SS:cs (minutes:seconds:centiseconds)."""
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    return f"{minutes:02d}:{sec:02d}:{centis:02d}"


class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter Media Player")

        # Playback timing state
        self.video_offset = 0.0
        self.playback_started_at = None

        # Slider state
        self.slider_dragging = False
        self.was_playing = False

        # Initialize video player widget
        self.vid_player = TkinterVideo(scaled=True, master=root)
        self.vid_player.pack(expand=True, fill="both")
        self.vid_player.bind("<<Duration>>", self.update_duration)
        self.vid_player.bind("<<Ended>>", self.video_ended)

        # Build control UI
        self.build_controls()

        # Load the video and schedule playback startup
        video_path = str(DATA_DIR / "videos" / "athlete_1.mp4")
        self.vid_player.load(video_path)
        self.root.after(100, self.start_playback)

        # Instead of a 10ms interval, update every 33ms (~30fps)
        self.root.after(33, self.update_slider)

    def build_controls(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", padx=5, pady=5)

        self.play_pause_btn = tk.Button(control_frame, text="Play", command=self.play_pause)
        self.play_pause_btn.pack(side="left")

        tk.Button(control_frame, text="Skip -5 sec", command=lambda: self.skip(-5)).pack(side="left")

        self.start_time = tk.Label(control_frame, text="00:00:00")
        self.start_time.pack(side="left", padx=5)

        # Update slider resolution to match frame rate (1/30 ≈ 0.033 sec)
        self.progress_slider = tk.Scale(
            control_frame, from_=0, to=0, orient="horizontal",
            resolution=0.033, showvalue=0, length=300
        )
        self.progress_slider.bind("<ButtonPress-1>", self.slider_press)
        self.progress_slider.bind("<B1-Motion>", self.slider_motion)
        self.progress_slider.bind("<ButtonRelease-1>", self.slider_release)
        # Disable right-click
        self.progress_slider.bind("<Button-3>", lambda event: "break")
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=5)

        self.end_time = tk.Label(control_frame, text="00:00:00")
        self.end_time.pack(side="left", padx=5)

        tk.Button(control_frame, text="Skip +5 sec", command=lambda: self.skip(5)).pack(side="left")

    def update_duration(self, event):
        duration = self.vid_player.video_info()["duration"]
        self.end_time.config(text=format_time(duration))
        self.progress_slider.config(to=duration)

    def get_current_time(self):
        if self.playback_started_at is not None:
            return self.video_offset + (time.time() - self.playback_started_at)
        return self.video_offset

    def update_slider(self):
        if not self.slider_dragging:
            current_time = self.get_current_time()
            self.progress_slider.set(current_time)
            self.start_time.config(text=format_time(current_time))
        # Update at ~33ms intervals to match 30fps
        self.root.after(33, self.update_slider)

    def slider_press(self, event):
        self.slider_dragging = True
        self.was_playing = (self.playback_started_at is not None)
        if self.was_playing:
            self.pause_video()
        self.update_slider_position(event)

    def slider_motion(self, event):
        self.update_slider_position(event)

    def slider_release(self, event):
        self.slider_dragging = False
        self.update_slider_position(event)
        self.video_offset = float(self.progress_slider.get())
        if self.was_playing:
            self.resume_video()

    def update_slider_position(self, event):
        widget = self.progress_slider
        width = widget.winfo_width()
        fraction = event.x / width if width > 0 else 0
        slider_from = float(widget["from"])
        slider_to = float(widget["to"])
        new_value = slider_from + (slider_to - slider_from) * fraction
        widget.set(new_value)
        self.vid_player.seek(new_value)
        # Update the left time label to reflect the slider's current position
        self.start_time.config(text=format_time(new_value))

    def skip(self, value: int):
        new_time = float(self.progress_slider.get()) + value
        self.video_offset = new_time
        self.vid_player.seek(new_time)
        self.progress_slider.set(new_time)

    def play_pause(self):
        if self.playback_started_at is None:
            self.resume_video()
        else:
            self.pause_video()

    def resume_video(self):
        self.vid_player.play()
        self.play_pause_btn.config(text="Pause")
        self.playback_started_at = time.time()

    def pause_video(self):
        if self.playback_started_at is not None:
            self.video_offset += time.time() - self.playback_started_at
        self.vid_player.pause()
        self.play_pause_btn.config(text="Play")
        self.playback_started_at = None

    def video_ended(self, event):
        self.progress_slider.set(self.progress_slider["to"])
        self.play_pause_btn.config(text="Play")
        self.progress_slider.set(0)
        self.video_offset = 0.0
        self.playback_started_at = None

    def start_playback(self):
        self.resume_video()
        self.play_pause_btn.config(text="Pause")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoPlayerApp(root)
    root.mainloop()
