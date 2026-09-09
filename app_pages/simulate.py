import streamlit as st

from app_lib import continue_to, load_raster_array, raster_mtime, require_value
from core.inundation import inundation_from_stage
from core.plots import inundation_triplet

require_value(
    "hand_path",
    "Compute HAND before simulating inundation.",
    "app_pages/hand.py",
    "Go to HAND model",
)

st.markdown(
    "Cells are inundated when HAND is at or below the water-surface stage. "
    "Depth is `max(stage − HAND, 0)`."
)

max_stage = st.number_input(
    "Maximum stage (m)",
    min_value=0.5,
    max_value=20.0,
    value=float(st.session_state.max_stage),
    step=0.5,
    key="max_stage_input",
    persist_state="session",
)
st.session_state.max_stage = float(max_stage)

stage = st.slider(
    "Stage (m)",
    min_value=0.0,
    max_value=float(st.session_state.max_stage),
    value=min(1.0, float(st.session_state.max_stage)),
    step=0.1,
    key="stage_m",
    persist_state="session",
)

hand = load_raster_array(st.session_state.hand_path, raster_mtime(st.session_state.hand_path))
inund, depth = inundation_from_stage(hand, stage)

flooded_pct = float(inund.mean() * 100.0)
finite_depth = depth[inund == 1]
max_depth = float(finite_depth.max()) if finite_depth.size else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Stage", f"{stage:.2f} m")
c2.metric("Inundated pixels", f"{flooded_pct:.2f}%")
c3.metric("Max depth", f"{max_depth:.2f} m")

st.pyplot(inundation_triplet(hand, inund, depth, stage), width="stretch")

continue_to("Continue to export", "app_pages/export.py")
