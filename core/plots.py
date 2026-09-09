"""Matplotlib figures for DEM, HAND, and inundation previews."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from core.rasters import downsample


def _new_figure(width: float = 7.5, height: float = 5.5) -> tuple[Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_axis_off()
    return fig, ax


def raster_figure(
    array: np.ndarray,
    title: str,
    cmap: str,
    colorbar_label: str,
    vmin: float | None = None,
    vmax: float | None = None,
) -> Figure:
    display = downsample(array)
    fig, ax = _new_figure()
    image = ax.imshow(display, interpolation="nearest", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label=colorbar_label)
    fig.tight_layout()
    return fig


def inundation_triplet(
    hand: np.ndarray,
    inund: np.ndarray,
    depth: np.ndarray,
    stage_m: float,
    cmap: str = "turbo",
) -> Figure:
    hand_d = downsample(hand)
    inund_d = downsample(inund)
    depth_d = downsample(depth)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6))
    panels = [
        (hand_d, "HAND (m)", cmap, None, None),
        (inund_d, f"Extent (stage = {stage_m:.2f} m)", cmap, 0, 1),
        (depth_d, "Depth (m): max(stage − HAND, 0)", cmap, None, None),
    ]
    for ax, (data, title, color, vmin, vmax) in zip(axes, panels):
        image = ax.imshow(data, interpolation="nearest", cmap=color, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_axis_off()
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig
