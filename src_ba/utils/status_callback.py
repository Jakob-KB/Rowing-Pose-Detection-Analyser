def status_callback(message: str = "Sample Message.", progress_value:int|None=None) -> tuple:
    # Example: Print the status update.

    if progress_value is not None:
        print(f"Status update: {message} | Progress: {progress_value}%")
    else:
        print(f"Status update: {message}")

    # Optionally, update a GUI element here, e.g.:
    # status_label.config(text=message)
    # progress_bar['value'] = progress

    return message, progress_value, code
