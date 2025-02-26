import streamlit as st


# --- PAGE SETUP ---
home_page = st.Page(
    "webpages/homepage.py",
    title="Home Page",
    default=True
)

# --- NAVIGATION SETUP [WITHOUT SECTIONS] ---
pg = st.navigation(pages=[home_page])


# --- RUN NAVIGATION ---
pg.run()