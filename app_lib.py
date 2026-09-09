"""Small Streamlit helpers shared by workflow pages."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import streamlit as st

from core.authentication import credentials_from_gee_key, initialize_earth_engine
from core.rasters import load_array


@st.cache_data(show_spinner=False, max_entries=8)
def load_raster_array(path: str, mtime: float) -> np.ndarray:
    array, _meta = load_array(path)
    return array


def raster_mtime(path: str | Path) -> float:
    return Path(path).stat().st_mtime


def continue_to(label: str, page: str) -> None:
    if st.button(label, icon=":material/arrow_forward:", type="primary"):
        st.switch_page(page)


def require_value(key: str, message: str, page: str, button_label: str) -> None:
    if st.session_state.get(key):
        return
    st.info(message)
    if st.button(button_label, icon=":material/arrow_forward:"):
        st.switch_page(page)
    st.stop()


def gee_key_from_secrets() -> dict | None:
    try:
        raw = st.secrets["gee_key"]
    except Exception:
        return None
    try:
        return credentials_from_gee_key(raw)
    except Exception:
        return None


def connect_earth_engine_from_secrets() -> tuple[bool, str | None]:
    """Initialize Earth Engine from ``st.secrets['gee_key']`` once per session."""
    if st.session_state.get("ee_ready"):
        return True, None

    account = gee_key_from_secrets()
    if account is None:
        return False, "Add a service account as `gee_key` in `.streamlit/secrets.toml`."

    project = str(account.get("project_id") or "").strip()
    client_email = str(account.get("client_email") or "").strip()
    try:
        initialize_earth_engine(project=project, service_account=account)
    except Exception as exc:
        st.session_state.ee_ready = False
        st.session_state.ee_error = str(exc)
        return False, str(exc)

    st.session_state.ee_ready = True
    st.session_state.ee_project = project
    st.session_state.ee_account = client_email
    st.session_state.ee_error = None
    return True, None
