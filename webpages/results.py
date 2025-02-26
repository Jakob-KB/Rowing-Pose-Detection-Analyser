import streamlit as st
from pathlib import Path

st.title("Session Results")

if "session" not in st.session_state:
    st.error("No session found. Please create a session first.")
else:
    session = st.session_state.session
    print(f"SESSION: {session}")
    st.header(f"Session: {session.title}")
    st.write("Here is the annotated video:")
    # Display the annotated video from the session folder.
    st.video(str(session.annotated_video_path))
    # Optionally, display metrics and graphs here.
