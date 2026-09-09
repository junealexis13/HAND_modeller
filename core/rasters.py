"""Raster I/O helpers shared by DEM, HAND, and inundation steps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS

NODATA_FLOOR = -9000.0


def load_array(path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    path = Path(path)
    with rasterio.open(path) as src:
        array = src.read(1).astype("float32")
        nodata = src.nodata
        profile = src.profile.copy()
        bounds = src.bounds
        crs = src.crs

    array = sanitize_nodata(array, nodata)
    meta = {
        "nodata": nodata,
        "profile": profile,
        "bounds": bounds,
        "crs": crs,
        "shape": array.shape,
        "min": float(np.nanmin(array)) if np.isfinite(array).any() else None,
        "max": float(np.nanmax(array)) if np.isfinite(array).any() else None,
        "nan_pct": float(np.isnan(array).mean() * 100.0),
    }
    return array, meta


def sanitize_nodata(array: np.ndarray, nodata: float | None) -> np.ndarray:
    out = array.astype("float32", copy=True)
    if nodata is not None:
        out[out == nodata] = np.nan
    out[out < NODATA_FLOOR] = np.nan
    return out


def write_geotiff(
    path: str | Path,
    array: np.ndarray,
    profile: dict[str, Any],
    dtype: str | np.dtype | type,
    nodata_val: float | int = 0,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prof = profile.copy()
    prof.update(dtype=dtype, count=1, nodata=nodata_val, compress="LZW")
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(array.astype(dtype), 1)
    return path


def downsample(array: np.ndarray, max_dim: int = 1200) -> np.ndarray:
    height, width = array.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return array
    step = int(np.ceil(longest / max_dim))
    return array[::step, ::step]


def crs_to_epsg4326_ok(crs: CRS | None) -> bool:
    if crs is None:
        return True
    try:
        return crs.to_epsg() == 4326
    except Exception:
        return str(crs).upper() in {"EPSG:4326", "WGS84"}
