import streamlit as st
import re
from pathlib import Path
import shutil
from src.config import SESSIONS_DIR, DATA_DIR, logger, TEMP_DIR
from src.session import Session
from src.video_processing.annotate_video import AnnotateVideo
from src.video_processing.pose_estimation import PoseEstimator  # assuming this is your pose detector
from src.utils.streamlit_handler import validate_session_title  # your validation function
import uuid
import time


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

    # Get inputs from the user
    session_title = st.text_input("Session Title", key="session_title_input")
    overwrite_existing_session = st.toggle("Overwrite Existing Session", key="overwrite_toggle")
    original_video_file = st.file_uploader("Video File", key="original_video", type="mp4")

    if st.button("Create Session", key="create_session_btn"):

        temp_video_path = save_temp_video_filepath(original_video_file)

        valid, error_msg = validate_session_title(session_title, overwrite=overwrite_existing_session)
        if not valid:
            st.error(error_msg)
        elif original_video_file is None:
            st.error("Please upload a video file.")
        else:
            with st.spinner("Processing session..."):
                try:
                    # Create a new session.
                    sample_session = Session(session_title, temp_video_path, overwrite=overwrite_existing_session)

                    # Process landmarks
                    pose_estimator = PoseEstimator(sample_session, overwrite=True)
                    pose_estimator.process_landmarks()

                    # Annotate the video.
                    annotator = AnnotateVideo(sample_session, overwrite=True)
                    annotator.annotate_video()

                    # Save the session in session state so the results page can access it.
                    st.session_state.session = sample_session
                except Exception as e:
                    st.error(f"Error creating session: {e}")
                    logger.error(f"Error creating session: {e}")
                    return
            st.success("Session processing complete!")
            # Navigate to the results page.
            st.session_state.page = "results"
            st.rerun()
