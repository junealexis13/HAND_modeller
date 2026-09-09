import streamlit as st

st.markdown(
    """
The **Height Above Nearest Drainage (HAND)** model measures how far each terrain
cell sits above the stream it would drain into. Flooded cells are those whose
HAND value is at or below a chosen water-surface stage.
"""
)

st.latex(r"HAND(c) = Z(c) - Z(\mathrm{Stream}_{target})")
st.latex(r"\mathrm{Inundation} = HAND \le \mathrm{stage}")

st.markdown(
    """
```mermaid
flowchart LR
  aoi[Area of interest] --> dem[Elevation model]
  dem --> hand[HAND]
  hand --> sim[Flood simulation]
  sim --> exp[Export rasters and GIF]
```
"""
)

st.subheader("How to run the workflow")
st.markdown(
    """
1. Connect Google Earth Engine only if you want a satellite DEM.
2. Set an area of interest from a bounding box or a KML / shapefile upload.
3. Download a DEM from Earth Engine, or upload your own GeoTIFF.
4. Compute HAND with a stream-fraction threshold.
5. Drag the stage slider to preview inundation extent and depth.
6. Export staged GeoTIFFs, a progression GIF, and a ZIP of depth rasters.
"""
)

ready = {
    "AOI": st.session_state.aoi is not None,
    "DEM": bool(st.session_state.dem_path),
    "HAND": bool(st.session_state.hand_path),
    "Stages": bool(st.session_state.stage_files),
}
cols = st.columns(4)
for column, (label, is_ready) in zip(cols, ready.items()):
    with column, st.container(border=True):
        status = "Ready" if is_ready else "Not started"
        st.metric(label, status)

st.caption(
    "Local DEM uploads do not require Earth Engine. Keep AOIs modest "
    "(a few hundred km²) when downloading from Earth Engine."
)

if st.button("Start with area of interest", icon=":material/crop_free:", type="primary"):
    st.switch_page("app_pages/aoi.py")
