import streamlit as st
import re
from pathlib import Path
import shutil
from src.config import SESSIONS_DIR, logger, TEMP_DIR
import uuid
from pathlib import Path
import shutil
from src.utils import validate_session_title, validate_raw_video


def save_temp_video_filepath(uploaded_file) -> Path:
    """
    Save the uploaded video file to the temporary directory (TEMP_DIR)
    using a unique file name to avoid collisions, and return the file path.
    """
    # Extract the file extension from the uploaded file's original name.
    original_extension = Path(uploaded_file.name).suffix

    # Generate a unique file name using uuid4.
    unique_filename = f"{uuid.uuid4()}{original_extension}"

    # Build the temporary file path.
    temp_video_path = Path(TEMP_DIR) / unique_filename
    temp_video_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file to the temp directory.
    with open(temp_video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    logger.info(f"Uploaded video saved to temporary location: {temp_video_path}")
    return temp_video_path


def create_new_session_form():
    st.header("Create New Session")


    # Group the inputs in a container (not a form)
    with st.container():
        session_title = st.text_input("Session Title", key="session_title_input")
        overwrite_existing_session = st.toggle("Overwrite Existing Session", key="overwrite_toggle")
        original_video_file = st.file_uploader("Video File", key="original_video", type="mp4")

        # The submit button is separate, so hitting Enter in the text input doesn't trigger it.
        if st.button("Create Session", key="create_session_btn"):

            # Save video to temp filepath and check video is valid
            temp_video_path = save_temp_video_filepath(original_video_file)
            valid, error_msg = validate_raw_video(temp_video_path)
            if not valid:
                st.error(error_msg)

            # Check session title is valid
            valid, error_msg = validate_session_title(session_title, overwrite=overwrite_existing_session)
            if not valid:
                st.error(error_msg)