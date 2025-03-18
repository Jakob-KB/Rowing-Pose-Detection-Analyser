import tkinter as tk
from tkinter import ttk
import threading
import shutil

from src.config import DATA_DIR
from src.modules.video_annotator import VideoAnnotator
from src.modules.cfr_video_processor import ProcessCFRVideo
from src.modules.landmark_processor import LandmarkProcessor
from src.modules.session_manager import SessionManager
from src.utils.exceptions import ProcessCancelled

from tkintervideoplayer import TkinterVideo


# StatusBar Component
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


# Pipeline Manager
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
        # Clear the video frame.
        for widget in self.video_frame.winfo_children():
            widget.destroy()
        # Create the robust video widget within the existing video frame.
        video_player = TkinterVideo(scaled=True, master=self.video_frame, consistant_frame_rate=True)
        video_player.load(str(video_path))
        video_player.pack(expand=True, fill="both")
        # Bind the <<Ended>> event so that the video loops when it finishes.
        video_player.bind("<<Ended>>", lambda e: video_player.play())
        video_player.play()

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


# Main Application
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
