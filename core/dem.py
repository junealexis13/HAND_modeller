"""Acquire and clip Digital Elevation Models from Earth Engine or a local GeoTIFF."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import ee
import numpy as np
import rasterio
import requests
from rasterio.mask import mask
from rasterio.warp import transform_geom

from core.paths import workspace_file
from core.rasters import load_array

GEE_DEM_SOURCES = {
    "JAXA ALOS AW3D30 v4.1": {
        "id": "JAXA/ALOS/AW3D30/V4_1",
        "kind": "collection",
        "band": "DSM",
        "scale": 30,
    },
    "NASA SRTM v3": {
        "id": "USGS/SRTMGL1_003",
        "kind": "image",
        "band": "elevation",
        "scale": 30,
    },
    "Copernicus GLO-30": {
        "id": "COPERNICUS/DEM/GLO30",
        "kind": "collection",
        "band": "DEM",
        "scale": 30,
    },
}


def download_gee_dem(
    aoi_geojson: dict[str, Any],
    out_path: str | Path | None = None,
    source: str = "JAXA ALOS AW3D30 v4.1",
    scale: int | None = None,
) -> Path:
    if source not in GEE_DEM_SOURCES:
        raise ValueError(f"Unknown DEM source: {source}")

    spec = GEE_DEM_SOURCES[source]
    out_path = Path(out_path) if out_path else workspace_file("dem_file.tif")
    region = ee.Geometry(aoi_geojson)
    scale = int(scale or spec["scale"])
    image = _gee_image(spec).clip(region).toFloat()

    url = image.getDownloadURL(
        {
            "scale": scale,
            "crs": "EPSG:4326",
            "region": region,
            "format": "GEO_TIFF",
            "filePerBand": False,
        }
    )
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    _write_gee_bytes(response.content, out_path)
    return out_path


def save_uploaded_dem(file_bytes: bytes, filename: str = "uploaded_dem.tif") -> Path:
    suffix = Path(filename).suffix.lower() or ".tif"
    out_path = workspace_file(f"uploaded_dem{suffix}")
    out_path.write_bytes(file_bytes)
    return out_path


def clip_dem_to_aoi(
    dem_path: str | Path,
    aoi_geojson: dict[str, Any],
    out_path: str | Path | None = None,
) -> Path:
    dem_path = Path(dem_path)
    out_path = Path(out_path) if out_path else workspace_file("clipped_dem.tif")

    with rasterio.open(dem_path) as src:
        geom = aoi_geojson
        if src.crs and str(src.crs).upper() not in {"EPSG:4326", "WGS84"}:
            geom = transform_geom("EPSG:4326", src.crs, aoi_geojson)
        out_img, out_transform = mask(src, [geom], crop=True)
        out_meta = src.meta.copy()

    out_meta.update(
        {
            "height": out_img.shape[1],
            "width": out_img.shape[2],
            "transform": out_transform,
            "compress": "LZW",
        }
    )
    with rasterio.open(out_path, "w", **out_meta) as dst:
        dst.write(out_img)
    return out_path


def describe_dem(dem_path: str | Path) -> dict[str, Any]:
    array, meta = load_array(dem_path)
    return {
        "path": str(dem_path),
        "shape": meta["shape"],
        "min": meta["min"],
        "max": meta["max"],
        "nan_pct": meta["nan_pct"],
        "crs": str(meta["crs"]) if meta["crs"] else "unknown",
        "bounds": meta["bounds"],
        "valid_pixels": int(np.isfinite(array).sum()),
    }


def _gee_image(spec: dict[str, Any]) -> ee.Image:
    if spec["kind"] == "image":
        image = ee.Image(spec["id"])
    else:
        image = ee.ImageCollection(spec["id"])
        if spec["band"]:
            image = image.select(spec["band"])
        return image.mosaic()
    if spec["band"]:
        image = image.select(spec["band"])
    return image


def _write_gee_bytes(content: bytes, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            tifs = [name for name in archive.namelist() if name.lower().endswith((".tif", ".tiff"))]
            if not tifs:
                raise ValueError("Earth Engine download did not contain a GeoTIFF.")
            out_path.write_bytes(archive.read(tifs[0]))
        return
    out_path.write_bytes(content)
