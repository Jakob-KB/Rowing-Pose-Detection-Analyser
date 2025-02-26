import streamlit as st

# --- PAGE SETUP ---
home_page = st.Page(
    "webpages/homepage.py",
    title="Home Page",
    default=True
)
results_page = st.Page(
    "webpages/results.py",
    title="Results Page"
)

# --- NAVIGATION SETUP ---
pg = st.navigation(pages=[home_page, results_page])

# --- RUN NAVIGATION ---
pg.run()