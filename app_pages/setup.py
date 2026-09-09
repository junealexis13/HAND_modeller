import streamlit as st

from app_lib import connect_earth_engine_from_secrets, continue_to, gee_key_from_secrets

st.markdown(
    "Earth Engine is initialized from the `gee_key` service account in "
    "`.streamlit/secrets.toml`. You only need this page if the automatic "
    "connection failed or you want to confirm the project."
)

ready, error = connect_earth_engine_from_secrets()
account = gee_key_from_secrets()

if ready:
    st.badge("Earth Engine connected", color="green", icon=":material/check_circle:")
    st.metric("Google Cloud project", st.session_state.ee_project or "unknown")
    if st.session_state.ee_account:
        st.caption(f"Service account: `{st.session_state.ee_account}`")
else:
    st.badge("Not connected", color="gray", icon=":material/cloud_off:")
    if error:
        st.error(error)
    if account is None:
        st.info(
            "Put a Google service account JSON object in `.streamlit/secrets.toml` "
            "under `[gee_key]`, including `project_id`, `client_email`, and `private_key`."
        )

if st.button("Retry connection", icon=":material/refresh:"):
    st.session_state.ee_ready = False
    st.session_state.ee_error = None
    st.rerun()

continue_to("Continue to area of interest", "app_pages/aoi.py")
