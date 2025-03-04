class CancelableProcess:
    def __init__(self):
        self._cancelled = False
        self._progress_callback = None

    def cancel(self):
        """Trigger cancellation."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def set_progress_callback(self, callback):
        """
        Set a progress callback function accepting two parameters:
        message (str) and progress (float).
        """
        self._progress_callback = callback

    def report_progress(self, message: str, progress: float):
        if self._progress_callback:
            self._progress_callback(message, progress)