import streamlit as st

from app_lib import continue_to, load_raster_array, raster_mtime, require_value
from core.hand import compute_hand
from core.paths import workspace_file
from core.plots import raster_figure
from core.session import clear_downstream

require_value(
    "dem_path",
    "Acquire or upload a DEM before computing HAND.",
    "app_pages/dem.py",
    "Go to elevation model",
)

st.markdown(
    "HAND follows flow paths from every cell to the nearest drainage. "
    "The stream fraction controls how much of the landscape is treated as a channel: "
    "start near **0.017** and raise it if the network looks too sparse."
)

with st.form("hand_form"):
    stream_frac = st.slider(
        "Stream fraction",
        min_value=0.0005,
        max_value=0.08,
        value=float(st.session_state.stream_frac),
        step=0.0005,
        help="Approximate share of DEM pixels classified as streams.",
        format="%.4f",
    )
    submitted = st.form_submit_button("Compute HAND", icon=":material/water:")

if submitted:
    st.session_state.stream_frac = float(stream_frac)
    with st.status("Computing HAND. This can take a minute on large DEMs...", expanded=True) as status:
        st.write("Filling pits and depressions")
        st.write("Computing flow direction, accumulation, and HAND")
        try:
            info = compute_hand(
                st.session_state.dem_path,
                stream_frac=float(stream_frac),
                out_hand=workspace_file("hand_file.tif"),
            )
        except Exception as exc:
            status.update(label="HAND computation failed", state="error")
            st.error(str(exc))
        else:
            st.session_state.hand_path = info["hand_path"]
            st.session_state.hand_info = info
            clear_downstream(st.session_state, "hand_path")
            status.update(label="HAND raster saved", state="complete")

if not st.session_state.hand_path:
    st.stop()

info = st.session_state.hand_info
c1, c2, c3, c4 = st.columns(4)
c1.metric("Accumulation threshold", f"{info['threshold']:.0f}")
c2.metric("Stream pixels", f"{info['stream_pct']:.2f}%")
c3.metric("HAND min / max", f"{info['hand_min']:.2f} / {info['hand_max']:.2f} m")
c4.metric("No-data", f"{info['hand_nan_pct']:.1f}%")

if info["stream_pct"] > 15:
    st.warning("A large share of pixels are streams. Lower the stream fraction.")
elif info["stream_pct"] < 0.2:
    st.warning("Very few stream pixels were found. Raise the stream fraction.")

array = load_raster_array(st.session_state.hand_path, raster_mtime(st.session_state.hand_path))
st.pyplot(raster_figure(array, "HAND (m)", "hot", "m above drainage"), width="stretch")

continue_to("Continue to flood simulation", "app_pages/simulate.py")
