from pathlib import Path

import streamlit as st

from app_lib import require_value
from core.inundation import build_progression_gif, write_stage_rasters, zip_depth_rasters
from core.paths import workspace_file

require_value(
    "hand_path",
    "Compute HAND before exporting flood rasters.",
    "app_pages/hand.py",
    "Go to HAND model",
)

st.markdown(
    "Generate evenly spaced stage rasters, a flood-progression GIF, and a ZIP of "
    "depth / extent GeoTIFFs."
)

with st.form("export_form"):
    max_stage = st.number_input(
        "Maximum stage (m)",
        min_value=0.5,
        max_value=20.0,
        value=float(st.session_state.max_stage),
        step=0.5,
    )
    interval = st.slider(
        "Number of stage frames",
        min_value=3,
        max_value=30,
        value=int(st.session_state.stage_interval),
    )
    zip_stem = st.text_input("Export name", value="hand_model")
    terrain_cmap = st.selectbox(
        "Terrain colormap",
        options=["terrain", "gist_earth", "gray", "copper", "bone"],
    )
    submitted = st.form_submit_button("Generate exports", icon=":material/movie:")

if submitted:
    st.session_state.max_stage = float(max_stage)
    st.session_state.stage_interval = int(interval)
    with st.status("Writing stage rasters and animation...", expanded=True) as status:
        try:
            st.write("Writing extent and depth GeoTIFFs")
            outputs = write_stage_rasters(
                st.session_state.hand_path,
                max_stage=float(max_stage),
                interval=int(interval),
            )
            st.write(f"{len(outputs)} stages: {[stage for stage, *_ in outputs]}")
            st.write("Rendering progression GIF")
            gif_path = build_progression_gif(
                outputs,
                dem_path=st.session_state.dem_path,
                max_inundation_depth=float(max_stage),
                gif_path=workspace_file("flood_progression.gif"),
                terrain_colormap=terrain_cmap,
            )
            zip_path = zip_depth_rasters(outputs, zip_name=f"{zip_stem}_depths.zip")
        except Exception as exc:
            status.update(label="Export failed", state="error")
            st.error(str(exc))
        else:
            st.session_state.stage_files = [
                (stage, str(extent), str(depth)) for stage, extent, depth in outputs
            ]
            st.session_state.gif_path = str(gif_path)
            st.session_state.export_zip_path = str(zip_path)
            status.update(label="Exports ready", state="complete")

if st.session_state.gif_path and Path(st.session_state.gif_path).exists():
    st.image(st.session_state.gif_path, caption="Flood progression")

downloads = st.container(horizontal=True)
if st.session_state.hand_path and Path(st.session_state.hand_path).exists():
    downloads.download_button(
        "HAND GeoTIFF",
        data=Path(st.session_state.hand_path).read_bytes(),
        file_name="hand.tif",
        mime="image/tiff",
        icon=":material/download:",
    )
if st.session_state.gif_path and Path(st.session_state.gif_path).exists():
    downloads.download_button(
        "Progression GIF",
        data=Path(st.session_state.gif_path).read_bytes(),
        file_name="flood_progression.gif",
        mime="image/gif",
        icon=":material/movie:",
    )
if st.session_state.export_zip_path and Path(st.session_state.export_zip_path).exists():
    zip_path = Path(st.session_state.export_zip_path)
    downloads.download_button(
        "Depth and extent ZIP",
        data=zip_path.read_bytes(),
        file_name=zip_path.name,
        mime="application/zip",
        icon=":material/folder_zip:",
    )

if st.session_state.stage_files:
    st.caption(f"{len(st.session_state.stage_files)} stage rasters are in `data/workspace/`.")
