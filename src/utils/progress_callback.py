# src/utils/progress_callback.py

import sys


def progress_callback(stage: str, progress: float) -> None:
    """A CLI progress callback function to inform the user about the status of a session."""
    sys.stdout.write(f"\r{stage}: {progress:.2f}% completed")
    sys.stdout.flush()

    if progress >= 100:
        sys.stdout.write("\n")
        sys.stdout.flush()