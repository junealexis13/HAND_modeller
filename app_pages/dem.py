import streamlit as st

from app_lib import continue_to, load_raster_array, raster_mtime
from core.dem import GEE_DEM_SOURCES, clip_dem_to_aoi, describe_dem, download_gee_dem, save_uploaded_dem
from core.paths import workspace_file
from core.plots import raster_figure
from core.session import clear_downstream

st.markdown(
    "Use a satellite DEM from Earth Engine, or upload a GeoTIFF. If you upload a DEM, "
    "you can optionally clip it to the AOI from the previous step."
)

source_mode = st.segmented_control(
    "DEM source",
    options=["Earth Engine", "Upload GeoTIFF"],
    default="Earth Engine",
    required=True,
    key="dem_mode",
    persist_state="session",
)

if source_mode == "Earth Engine":
    if not st.session_state.ee_ready:
        st.info("Connect Earth Engine before downloading a satellite DEM.")
        if st.button("Go to Earth Engine", icon=":material/cloud:"):
            st.switch_page("app_pages/setup.py")
        st.stop()
    if st.session_state.aoi is None:
        st.info("Set an area of interest before downloading a DEM.")
        if st.button("Go to area of interest", icon=":material/crop_free:"):
            st.switch_page("app_pages/aoi.py")
        st.stop()

    with st.form("gee_dem_form"):
        dataset = st.selectbox("Dataset", list(GEE_DEM_SOURCES.keys()))
        scale = st.number_input("Pixel size (m)", min_value=10, max_value=90, value=30, step=5)
        submitted = st.form_submit_button("Download DEM", icon=":material/satellite:")
    if submitted:
        with st.status("Downloading DEM from Earth Engine...", expanded=True) as status:
            st.write(f"Dataset: {dataset}")
            st.write(f"Scale: {scale} m")
            try:
                path = download_gee_dem(
                    st.session_state.aoi,
                    out_path=workspace_file("dem_file.tif"),
                    source=dataset,
                    scale=int(scale),
                )
                info = describe_dem(path)
            except Exception as exc:
                status.update(label="DEM download failed", state="error")
                st.error(str(exc))
            else:
                st.session_state.dem_path = str(path)
                st.session_state.dem_source = dataset
                st.session_state.dem_info = info
                clear_downstream(st.session_state, "dem_path")
                status.update(label="DEM downloaded", state="complete")
else:
    uploaded = st.file_uploader("DEM GeoTIFF", type=["tif", "tiff"])
    clip = st.checkbox(
        "Clip to current AOI",
        value=st.session_state.aoi is not None,
        disabled=st.session_state.aoi is None,
    )
    if uploaded is not None and st.button("Use uploaded DEM", icon=":material/upload:"):
        with st.status("Preparing uploaded DEM...", expanded=True) as status:
            try:
                path = save_uploaded_dem(uploaded.getvalue(), uploaded.name)
                if clip and st.session_state.aoi is not None:
                    st.write("Clipping to AOI")
                    path = clip_dem_to_aoi(path, st.session_state.aoi)
                info = describe_dem(path)
            except Exception as exc:
                status.update(label="Could not read DEM", state="error")
                st.error(str(exc))
            else:
                st.session_state.dem_path = str(path)
                st.session_state.dem_source = uploaded.name
                st.session_state.dem_info = info
                clear_downstream(st.session_state, "dem_path")
                status.update(label="DEM ready", state="complete")

if not st.session_state.dem_path:
    st.stop()

info = st.session_state.dem_info or describe_dem(st.session_state.dem_path)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Shape", f"{info['shape'][0]} × {info['shape'][1]}")
c2.metric("Min elevation", f"{info['min']:.1f} m" if info["min"] is not None else "n/a")
c3.metric("Max elevation", f"{info['max']:.1f} m" if info["max"] is not None else "n/a")
c4.metric("No-data", f"{info['nan_pct']:.1f}%")
st.caption(f"Source: {st.session_state.dem_source} · CRS: {info['crs']}")

array = load_raster_array(st.session_state.dem_path, raster_mtime(st.session_state.dem_path))
st.pyplot(raster_figure(array, "Project DEM", "terrain", "Elevation (m)"), width="stretch")

continue_to("Continue to HAND model", "app_pages/hand.py")
