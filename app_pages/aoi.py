import pandas as pd
import streamlit as st

from core.aoi import aoi_area_km2, bbox_to_geojson, geojson_bounds, geojson_centroid, load_aoi_from_file
from core.paths import workspace_file
from core.session import DEFAULT_BBOX, clear_downstream

st.markdown(
    "Define the catchment or study area. You can type a bounding box or upload a "
    "KML, GeoJSON, or zipped shapefile."
)

mode = st.segmented_control(
    "AOI source",
    options=["Bounding box", "Upload file"],
    default="Bounding box",
    required=True,
    key="aoi_mode",
    persist_state="session",
)

aoi = None
source = None

if mode == "Upload file":
    uploaded = st.file_uploader(
        "KML, GeoJSON, or shapefile ZIP",
        type=["kml", "zip", "geojson", "json"],
    )
    if uploaded is not None:
        dest = workspace_file(uploaded.name)
        dest.write_bytes(uploaded.getvalue())
        try:
            aoi = load_aoi_from_file(dest)
            source = uploaded.name
        except Exception as exc:
            st.error(str(exc))
else:
    with st.form("bbox_form"):
        current = st.session_state.aoi
        if current is not None:
            west, south, east, north = geojson_bounds(current)
        else:
            west = DEFAULT_BBOX["west"]
            south = DEFAULT_BBOX["south"]
            east = DEFAULT_BBOX["east"]
            north = DEFAULT_BBOX["north"]

        c1, c2 = st.columns(2)
        with c1:
            west = st.number_input("West", value=float(west), format="%.6f")
            south = st.number_input("South", value=float(south), format="%.6f")
        with c2:
            east = st.number_input("East", value=float(east), format="%.6f")
            north = st.number_input("North", value=float(north), format="%.6f")
        submitted = st.form_submit_button("Set bounding box", icon=":material/crop_free:")
    if submitted:
        try:
            aoi = bbox_to_geojson(west, south, east, north)
            source = "bounding box"
        except Exception as exc:
            st.error(str(exc))

if aoi is not None:
    previous = st.session_state.aoi
    st.session_state.aoi = aoi
    st.session_state.aoi_source = source
    if previous != aoi:
        clear_downstream(st.session_state, "aoi")

if st.session_state.aoi is None:
    st.caption("The default box is near Central Luzon, matching the reference notebook map center.")
    st.stop()

west, south, east, north = geojson_bounds(st.session_state.aoi)
area = aoi_area_km2(st.session_state.aoi)
lat, lon = geojson_centroid(st.session_state.aoi)

m1, m2, m3 = st.columns(3)
m1.metric("Width (deg)", f"{east - west:.4f}")
m2.metric("Height (deg)", f"{north - south:.4f}")
m3.metric("Approx. area", f"{area:.1f} km²")

if area > 2000:
    st.warning(
        "This AOI is large for an Earth Engine GeoTIFF download. "
        "Clip further, or upload a local DEM."
    )

st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), height=320)
with st.expander("GeoJSON"):
    st.json(st.session_state.aoi)

if st.button("Continue to elevation model", icon=":material/arrow_forward:", type="primary"):
    st.switch_page("app_pages/dem.py")
