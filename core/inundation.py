"""Stage-based inundation rasters, flood-progression GIF, and ZIP export."""

from __future__ import annotations

import zipfile
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
import rasterio

from core.paths import workspace_file, workspace_dir
from core.rasters import downsample, load_array, sanitize_nodata, write_geotiff


def inundation_from_stage(hand: np.ndarray, stage_m: float) -> tuple[np.ndarray, np.ndarray]:
    finite = np.isfinite(hand)
    inund = np.where(finite & (hand <= stage_m), 1, 0).astype(np.uint8)
    depth = np.where(finite, np.maximum(stage_m - hand, 0), np.nan).astype(np.float32)
    return inund, depth


def stage_levels(max_stage: float, interval: int) -> list[float]:
    if interval < 2:
        raise ValueError("Interval count must be at least 2.")
    levels = np.linspace(0.1, float(max_stage), int(interval), dtype="float64")
    return [round(float(value), 2) for value in levels]


def write_stage_rasters(
    hand_path: str | Path,
    max_stage: float,
    interval: int,
) -> list[tuple[float, Path, Path]]:
    hand_arr, meta = load_array(hand_path)
    profile = meta["profile"]
    out_dir = workspace_dir()

    for pattern in ("hand_extent_stage_*.tif", "hand_depth_stage_*.tif"):
        for old in out_dir.glob(pattern):
            old.unlink(missing_ok=True)

    outputs: list[tuple[float, Path, Path]] = []
    for stage in stage_levels(max_stage, interval):
        inund, depth = inundation_from_stage(hand_arr, stage)
        depth = np.where(inund == 1, depth, 0).astype(np.float32)
        ext_path = out_dir / f"hand_extent_stage_{stage:.2f}m.tif"
        dep_path = out_dir / f"hand_depth_stage_{stage:.2f}m.tif"
        write_geotiff(ext_path, inund, profile, dtype=rasterio.uint8, nodata_val=0)
        write_geotiff(dep_path, depth, profile, dtype=rasterio.float32, nodata_val=0)
        outputs.append((stage, ext_path, dep_path))
    return outputs


def build_progression_gif(
    stage_files: list[tuple[float, Path, Path]],
    dem_path: str | Path | None,
    max_inundation_depth: float,
    gif_path: str | Path | None = None,
    terrain_colormap: str = "terrain",
    water_colormap: str = "berlin_r",
) -> Path:
    gif_path = Path(gif_path) if gif_path else workspace_file("flood_progression.gif")
    bg_data = None
    bg_extent = None
    if dem_path and Path(dem_path).exists():
        with rasterio.open(dem_path) as bg_src:
            bg_data = sanitize_nodata(bg_src.read(1).astype("float32"), bg_src.nodata)
            bounds = bg_src.bounds
            bg_extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            bg_data = downsample(bg_data)

    try:
        plt.get_cmap(water_colormap)
    except ValueError:
        water_colormap = "turbo"

    frames: list[np.ndarray] = []
    sorted_files = sorted(stage_files, key=lambda item: float(item[0]))

    for stage_raw, _extent_path, depth_path in sorted_files:
        stage = float(stage_raw)
        with rasterio.open(depth_path) as src:
            depth = src.read(1).astype("float32")
            nodata = src.nodata
            bounds = src.bounds
            depth_extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

        valid = np.isfinite(depth)
        if nodata is not None:
            valid &= depth != nodata
        valid &= depth > 0

        depth_display = np.zeros(depth.shape, dtype=np.uint8)
        if np.any(valid):
            scaled = np.clip(depth[valid] / max(max_inundation_depth, 1e-6), 0, 1)
            depth_display[valid] = np.maximum(1, np.round(scaled * 255)).astype(np.uint8)

        fig, ax = plt.subplots(figsize=(7, 7), dpi=110)
        fig.patch.set_facecolor("#1e1e1e")
        ax.set_facecolor("#1e1e1e")

        display_extent = bg_extent if bg_extent is not None else depth_extent
        if bg_data is not None:
            ax.imshow(bg_data, cmap=terrain_colormap, alpha=0.65, extent=bg_extent)

        masked = np.where(depth_display == 0, np.nan, depth_display)
        masked = downsample(masked)
        image = ax.imshow(
            masked,
            vmin=1,
            vmax=255,
            cmap=water_colormap,
            alpha=0.85,
            extent=display_extent,
        )
        ax.set_title(
            f"Flood inundation stage: {stage:.2f} m",
            color="white",
            fontsize=14,
            pad=10,
            weight="bold",
        )
        ax.axis("off")
        cbar = fig.colorbar(image, ax=ax, shrink=0.65, pad=0.03, orientation="horizontal")
        cbar.set_label("Flood depth (m)", color="white", fontsize=10)
        cbar.ax.xaxis.set_tick_params(color="white", labelcolor="white")
        cbar.outline.set_edgecolor("white")
        cbar.set_ticks([1, 128, 255])
        cbar.set_ticklabels(["0.1 m", f"{max_inundation_depth / 2:.1f} m", f"{max_inundation_depth:.1f} m"])
        fig.tight_layout()
        fig.canvas.draw()
        frame = np.asarray(fig.canvas.buffer_rgba())
        frames.append(frame[:, :, :3].copy())
        plt.close(fig)

    imageio.mimsave(gif_path, frames, fps=2, loop=0)
    return gif_path


def zip_depth_rasters(
    stage_files: list[tuple[float, Path, Path]],
    zip_name: str = "hand_depths.zip",
) -> Path:
    zip_path = workspace_file(zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for stage, _extent_path, depth_path in stage_files:
            archive.write(depth_path, arcname=f"{float(stage):.2f}m.tif")
            extent_path = _extent_path
            archive.write(extent_path, arcname=f"{float(stage):.2f}m_extent.tif")
    return zip_path
