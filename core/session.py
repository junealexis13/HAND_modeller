"""Shared Streamlit session-state defaults and workflow status."""

from __future__ import annotations

from typing import Any

DEFAULT_BBOX = {
    "west": 120.94,
    "south": 15.43,
    "east": 121.01,
    "north": 15.49,
}

SESSION_DEFAULTS: dict[str, Any] = {
    "ee_project": "",
    "ee_ready": False,
    "ee_account": None,
    "ee_error": None,
    "aoi": None,
    "aoi_source": None,
    "dem_path": None,
    "dem_source": None,
    "dem_info": None,
    "hand_path": None,
    "hand_info": None,
    "stream_frac": 0.017,
    "max_stage": 3.0,
    "stage_interval": 14,
    "stage_files": None,
    "gif_path": None,
    "export_zip_path": None,
}


DOWNSTREAM_KEYS = {
    "aoi": [
        "dem_path",
        "dem_source",
        "dem_info",
        "hand_path",
        "hand_info",
        "stage_files",
        "gif_path",
        "export_zip_path",
    ],
    "dem_path": ["hand_path", "hand_info", "stage_files", "gif_path", "export_zip_path"],
    "hand_path": ["stage_files", "gif_path", "export_zip_path"],
}


def workflow_steps(state: Any) -> list[tuple[str, bool]]:
    return [
        ("Earth Engine", bool(state.get("ee_ready"))),
        ("Area of interest", state.get("aoi") is not None),
        ("Digital elevation", bool(state.get("dem_path"))),
        ("HAND model", bool(state.get("hand_path"))),
        ("Flood stages", bool(state.get("stage_files"))),
    ]


def clear_downstream(state: Any, from_key: str) -> None:
    for key in DOWNSTREAM_KEYS.get(from_key, []):
        state[key] = SESSION_DEFAULTS[key]
