import tkinter as tk
from tkinter import ttk
import threading
import shutil
import datetime
import vlc  # Requires python-vlc installed

# Project-specific imports; adjust paths as needed.
from src.config import DATA_DIR
from src.modules.video_annotator import VideoAnnotator
from src.modules.cfr_video_processor import ProcessCFRVideo
from src.modules.landmark_processor import LandmarkProcessor
from src.modules.session_manager import SessionManager
from src.utils.exceptions import ProcessCancelled

# --- StatusBar Component ---
class StatusBar(tk.Frame):
    def __init__(self, parent, fixed_height=25, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.config(height=fixed_height, relief=tk.SUNKEN, borderwidth=1)
        self.pack_propagate(False)  # Keep fixed height.
        self.status_label = tk.Label(self, text="Idle", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='determinate', length=200)
        self.progress_bar.pack_forget()  # Hide initially.

    def update_status(self, message, progress_value=None):
        self.status_label.config(text=message)
        if progress_value is not None:
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side=tk.RIGHT, padx=5, pady=5)
            self.progress_bar['value'] = progress_value
        else:
            if self.progress_bar.winfo_ismapped():
                self.progress_bar.pack_forget()

# --- EmbeddedVideoPlayer Component using VLC (Simplified: Only Play/Pause) ---
class EmbeddedVideoPlayer(tk.Frame):
    def __init__(self, parent, video_path, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.video_path = video_path
        self.is_paused = True

        # Create VLC instance and player.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        # Attach an event to loop the video when it ends.
        self.events = self.player.event_manager()
        self.events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

        # Create canvas for video display.
        self.canvas = tk.Canvas(self, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Simple control panel with only a play/pause button.
        control_panel = tk.Frame(self)
        control_panel.pack(fill=tk.X, padx=5, pady=5)
        self.play_pause_btn = tk.Button(control_panel, text="Play", command=self.toggle_play_pause)
        self.play_pause_btn.pack(side=tk.LEFT, padx=5)

        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        # Set VLC output to the canvas window.
        if hasattr(self.player, "set_hwnd"):  # Windows.
            self.player.set_hwnd(self.canvas.winfo_id())
        else:
            self.player.set_xwindow(self.canvas.winfo_id())

    def _on_end_reached(self, event):
        # Loop: restart playback.
        self.player.stop()
        self.player.play()

    def toggle_play_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_btn.config(text="Play")
            self.is_paused = True
        else:
            self.player.play()
            self.play_pause_btn.config(text="Pause")
            self.is_paused = False

    def load_and_play(self):
        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)
        self.player.play()
        self.play_pause_btn.config(text="Pause")
        self.is_paused = False

# --- PipelineManager ---
class PipelineManager:
    def __init__(self, status_bar, start_button, video_frame):
        self.status_bar = status_bar
        self.start_button = start_button
        self.video_frame = video_frame
        self.cancel_requested = False
        self.thread = None
        self.session_manager = SessionManager()
        self.cfr_video_processor = ProcessCFRVideo()
        self.landmark_processor = LandmarkProcessor()
        self.video_annotator = VideoAnnotator()
        self.session = None

    def run(self):
        self.start_button.config(state="disabled")
        self.cancel_requested = False
        self.thread = threading.Thread(target=self._run_pipeline)
        self.thread.start()

    def _update_status(self, message="Sample Message.", progress_value=None):
        self.status_bar.update_status(message, progress_value)

    def _run_pipeline(self):
        try:
            session_title = "test_session"
            original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"
            self.session = self.session_manager.create_session(
                session_title=session_title,
                original_video_path=original_video_path,
                overwrite=True
            )
            video_metadata = self.cfr_video_processor.run(
                input_video_path=original_video_path,
                output_video_path=self.session.files.raw_video,
                status=self._update_status
            )
            self.session.video_metadata = video_metadata
            landmark_data = self.landmark_processor.run(
                raw_video_path=self.session.files.raw_video,
                video_metadata=self.session.video_metadata,
                file_path=self.session.files.landmark_data,
                status=self._update_status
            )
            self.video_annotator.run(
                raw_video_path=self.session.files.raw_video,
                annotated_video_path=self.session.files.annotated_video,
                video_metadata=self.session.video_metadata,
                landmark_data=landmark_data,
                status=self._update_status
            )
            self._open_video_player(self.session.files.annotated_video)
        except ProcessCancelled as e:
            self._update_status(message=str(e))
        except Exception as e:
            self._update_status(message=f"Error: {e}")
        finally:
            self.start_button.after(0, lambda: self.start_button.config(state="normal"))
            self._update_status(message="Idle")

    def _open_video_player(self, video_path):
        # Clear the video frame and embed the player.
        for widget in self.video_frame.winfo_children():
            widget.destroy()
        video_player = EmbeddedVideoPlayer(self.video_frame, str(video_path))
        video_player.pack(fill=tk.BOTH, expand=True)
        video_player.load_and_play()

    def cancel(self):
        self.cancel_requested = True
        self.cfr_video_processor.cancel()
        self.landmark_processor.cancel()
        self.video_annotator.cancel()
        if self.session is not None:
            self._delete_session_async(self.session.directory)

    def _delete_session_async(self, session_directory, attempts=10, delay=500):
        try:
            shutil.rmtree(session_directory)
            self._update_status("Session deleted.", progress_value=None)
        except PermissionError as e:
            if attempts > 0:
                self.status_bar.after(delay,
                    lambda: self._delete_session_async(session_directory, attempts - 1, delay))
            else:
                self._update_status(f"Failed to delete session: {e}", progress_value=None)

# --- Main Application ---
def main():
    root = tk.Tk()
    root.title("Video Processing Pipeline")
    root.geometry("800x600")

    # Main content frame.
    content_frame = tk.Frame(root)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Button frame at the top.
    button_frame = tk.Frame(content_frame)
    button_frame.pack(side=tk.TOP, pady=(0, 10))
    start_button = tk.Button(button_frame, text="Start")
    start_button.pack(side=tk.LEFT, padx=10)
    cancel_button = tk.Button(button_frame, text="Cancel")
    cancel_button.pack(side=tk.LEFT, padx=10)

    # Video frame for embedded video player.
    video_frame = tk.Frame(content_frame, bg="gray")
    video_frame.pack(fill=tk.BOTH, expand=True)

    # StatusBar at the bottom.
    status_bar = StatusBar(root, fixed_height=25)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    pipeline_manager = PipelineManager(status_bar, start_button, video_frame)
    start_button.config(command=pipeline_manager.run)
    cancel_button.config(command=pipeline_manager.cancel)

    root.mainloop()

if __name__ == "__main__":
    main()
