"""Google Earth Engine initialization for the Streamlit app."""

from __future__ import annotations

import json
from typing import Any, Mapping

import ee


def mapping_to_dict(value: Any) -> Any:
    """Convert Streamlit AttrDict / nested mappings into plain JSON-safe dicts."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)
        return value
    if isinstance(value, Mapping):
        return {str(key): mapping_to_dict(item) for key, item in value.items()}
    return value


def credentials_from_gee_key(gee_key: Any) -> dict[str, Any]:
    account = mapping_to_dict(gee_key)
    if not isinstance(account, dict):
        raise ValueError("gee_key must be a service account object.")
    if account.get("type") != "service_account":
        raise ValueError("gee_key is not a Google service account.")
    if not account.get("client_email"):
        raise ValueError("gee_key is missing client_email.")
    if not account.get("private_key"):
        raise ValueError("gee_key is missing private_key.")
    return account


def initialize_earth_engine(
    project: str | None = None,
    service_account: dict[str, Any] | None = None,
) -> str:
    """Initialize Earth Engine with a Cloud project and optional service account.

    Interactive ``ee.Authenticate()`` is not used here because it blocks Streamlit.
    """
    if service_account:
        project = (project or service_account.get("project_id") or "").strip()
        if not project:
            raise ValueError("Earth Engine project ID is required.")
        email = service_account.get("client_email")
        credentials = ee.ServiceAccountCredentials(
            email,
            key_data=json.dumps(service_account),
        )
        ee.Initialize(credentials=credentials, project=project)
        return project

    project = (project or "").strip()
    if not project:
        raise ValueError("Earth Engine project ID is required.")
    ee.Initialize(project=project)
    return project


def is_initialized() -> bool:
    try:
        ee.data.getAssetRoots()
        return True
    except Exception:
        return False
