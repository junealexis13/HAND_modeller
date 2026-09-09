"""Height Above Nearest Drainage computation with pysheds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

# pysheds 0.5 still calls np.in1d, which was removed in NumPy 2.4+.
if not hasattr(np, "in1d"):
    np.in1d = np.isin

from pysheds.grid import Grid

from core.paths import workspace_file
from core.rasters import load_array, write_geotiff


def pick_stream_threshold(acc: np.ndarray, frac: float) -> float:
    """Choose a threshold so that approximately ``frac`` of pixels are streams."""
    values = acc.astype("float32")
    values[~np.isfinite(values)] = np.nan
    quantile = 100.0 * (1.0 - float(frac))
    return float(np.nanpercentile(values, quantile))


def compute_hand(
    dem_path: str | Path,
    stream_frac: float = 0.017,
    out_hand: str | Path | None = None,
) -> dict[str, Any]:
    dem_path = Path(dem_path)
    out_hand = Path(out_hand) if out_hand else workspace_file("hand_file.tif")

    grid = Grid.from_raster(str(dem_path))
    dem = grid.read_raster(str(dem_path)).astype("float32")
    dem = grid.fill_pits(dem)
    dem = grid.fill_depressions(dem)
    dem = grid.resolve_flats(dem)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    threshold = pick_stream_threshold(np.asarray(acc), frac=stream_frac)
    streams = acc >= threshold
    stream_pct = float(np.asarray(streams).mean() * 100.0)
    if stream_pct <= 0:
        raise ValueError(
            "No stream pixels were identified. Increase the stream fraction and try again."
        )

    hand = grid.compute_hand(fdir, dem, streams)
    hand_arr = np.asarray(hand, dtype="float32")
    nodata = np.float32(-9999)
    hand_write = np.where(np.isfinite(hand_arr), hand_arr, nodata).astype("float32")

    _, dem_meta = load_array(dem_path)
    write_geotiff(out_hand, hand_write, dem_meta["profile"], dtype="float32", nodata_val=-9999)

    finite = np.isfinite(hand_arr)
    return {
        "hand_path": str(out_hand),
        "threshold": threshold,
        "stream_pct": stream_pct,
        "hand_min": float(np.nanmin(hand_arr)) if finite.any() else None,
        "hand_max": float(np.nanmax(hand_arr)) if finite.any() else None,
        "hand_nan_pct": float(np.isnan(hand_arr).mean() * 100.0),
        "shape": tuple(hand_arr.shape),
    }
