import streamlit as st

from app_lib import connect_earth_engine_from_secrets
from core.session import SESSION_DEFAULTS, workflow_steps

st.set_page_config(
    page_title="HAND modeller",
    page_icon=":material/flood:",
    layout="wide",
)

for key, value in SESSION_DEFAULTS.items():
    st.session_state.setdefault(key, value)

connect_earth_engine_from_secrets()

page = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Overview", icon=":material/home:"),
        ],
        "Workflow": [
            st.Page("app_pages/setup.py", title="Earth Engine", icon=":material/cloud:"),
            st.Page("app_pages/aoi.py", title="Area of interest", icon=":material/crop_free:"),
            st.Page("app_pages/dem.py", title="Elevation model", icon=":material/terrain:"),
            st.Page("app_pages/hand.py", title="HAND model", icon=":material/water:"),
            st.Page("app_pages/simulate.py", title="Flood simulation", icon=":material/waves:"),
            st.Page("app_pages/export.py", title="Export", icon=":material/download:"),
        ],
    },
    position="sidebar",
)

st.title(page.title, icon=page.icon)

with st.sidebar:
    st.caption("Progress")
    for label, done in workflow_steps(st.session_state):
        icon = ":material/check_circle:" if done else ":material/radio_button_unchecked:"
        st.markdown(f"{icon} {label}")

page.run()
