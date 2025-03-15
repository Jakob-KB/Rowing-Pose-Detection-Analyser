import tkinter as tk
import threading

from src.config import DATA_DIR
from src.modules.annotate_video import AnnotateVideo
from src.modules.clone_cfr_video import CloneCFRVideo
from src.modules.process_landmarks import ProcessLandmarks
from src.modules.session_manager import SessionManager

class PipelineRunner:
    def __init__(self, status_label, start_button):
        self.status_label = status_label
        self.start_button = start_button
        self.cancel_requested = False
        self.thread = None

    def run(self):
        # Disable start button during processing.
        self.start_button.config(state="disabled")
        self.cancel_requested = False
        self.thread = threading.Thread(target=self._run_pipeline)
        self.thread.start()

    def _update_status(self, message):
        # Thread-safe update of the status label.
        self.status_label.after(0, lambda: self.status_label.config(text=message))

    def _check_cancel(self):
        if self.cancel_requested:
            raise Exception("Pipeline cancelled")

    def _run_pipeline(self):
        try:
            self._update_status("Starting pipeline...")

            # Define pipeline inputs and create objects.
            session_title = "test_session"
            original_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

            session_manager = SessionManager()
            clone_cfr_video = CloneCFRVideo()
            landmark_processor = ProcessLandmarks()
            annotator = AnnotateVideo()

            # Create session.
            self._update_status("Creating session...")
            session = session_manager.create_session(
                session_title=session_title,
                original_video_path=original_video_path,
                overwrite=True
            )
            self._check_cancel()

            # Clone video.
            self._update_status("Cloning video...")
            clone_cfr_video.run(
                input_video_path=original_video_path,
                output_video_path=session.files.raw_video
            )
            self._check_cancel()

            # Update and save session.
            self._update_status("Updating session...")
            session_manager.update_session(session)
            session_manager.save_session(session)
            self._check_cancel()

            # Process landmarks.
            self._update_status("Processing landmarks...")
            landmark_data = landmark_processor.run(
                raw_video_path=session.files.raw_video,
                video_metadata=session.video_metadata
            )
            self._check_cancel()

            # Save landmark data.
            self._update_status("Saving landmark data...")
            landmark_processor.save_landmark_data_to_file(
                landmark_data=landmark_data,
                file_path=session.files.landmark_data
            )
            self._check_cancel()

            # Annotate video.
            self._update_status("Annotating video...")
            annotator.run(
                raw_video_path=session.files.raw_video,
                annotated_video_path=session.files.annotated_video,
                video_metadata=session.video_metadata,
                landmark_data=landmark_data,
            )

            self._update_status("Pipeline completed!")
        except Exception as e:
            # Catch cancellation or other exceptions.
            self._update_status(f"Pipeline terminated: {str(e)}")
        finally:
            # Re-enable the start button when finished.
            self.start_button.after(0, lambda: self.start_button.config(state="normal"))

    def cancel(self):
        self.cancel_requested = True
        self._update_status("Cancellation requested...")

def main():
    root = tk.Tk()
    root.title("Video Processing Pipeline")

    # A label to show pipeline status.
    status_label = tk.Label(root, text="Idle", wraplength=300)
    status_label.pack(pady=10)

    # Create the PipelineRunner instance.
    # (start_button will be created next and passed into PipelineRunner)
    pipeline_runner = PipelineRunner(status_label, None)

    # Create Start and Cancel buttons.
    start_button = tk.Button(root, text="Start", command=pipeline_runner.run)
    start_button.pack(side=tk.LEFT, padx=10, pady=10)

    cancel_button = tk.Button(root, text="Cancel", command=pipeline_runner.cancel)
    cancel_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Now that the start_button is created, assign it to the pipeline_runner.
    pipeline_runner.start_button = start_button

    root.mainloop()

if __name__ == "__main__":
    main()
