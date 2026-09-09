"""Area-of-interest parsing from bounding boxes, KML, and shapefile ZIP files."""

from __future__ import annotations

import math
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import fiona
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def bbox_to_geojson(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    if west >= east or south >= north:
        raise ValueError("Bounding box must have west < east and south < north.")
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
        ],
    }


def geojson_bounds(geom: dict[str, Any]) -> tuple[float, float, float, float]:
    shapely_geom = shape(geom)
    west, south, east, north = shapely_geom.bounds
    return west, south, east, north


def geojson_centroid(geom: dict[str, Any]) -> tuple[float, float]:
    shapely_geom = shape(geom)
    centroid = shapely_geom.centroid
    return centroid.y, centroid.x


def aoi_area_km2(geom: dict[str, Any]) -> float:
    """Approximate planar area in km² from a WGS84 geometry."""
    from shapely.ops import transform

    shapely_geom = shape(geom)
    west, south, _east, north = shapely_geom.bounds
    lat_m = 111_320.0
    lon_m = 111_320.0 * math.cos(math.radians((south + north) / 2.0))

    def _to_m(x: float, y: float, z: float | None = None):
        mx = (x - west) * lon_m
        my = (y - south) * lat_m
        return (mx, my) if z is None else (mx, my, z)

    return float(transform(_to_m, shapely_geom).area) / 1_000_000.0


def load_aoi_from_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return _load_shapefile_zip(path)
    if suffix == ".kml":
        try:
            return _load_vector_with_fiona(path)
        except Exception:
            return _load_kml(path)
    if suffix in {".geojson", ".json", ".shp"}:
        return _load_vector_with_fiona(path)
    raise ValueError(f"Unsupported AOI file type: {path.suffix}")


def _load_shapefile_zip(zip_path: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(tmp)
        shp_files = list(Path(tmp).rglob("*.shp"))
        if not shp_files:
            raise ValueError("No .shp file found inside the ZIP archive.")
        return _load_vector_with_fiona(shp_files[0])


def _load_vector_with_fiona(path: Path) -> dict[str, Any]:
    with fiona.open(path) as source:
        geoms = [shape(feature["geometry"]) for feature in source if feature.get("geometry")]
    if not geoms:
        raise ValueError(f"No geometries found in {path.name}.")
    combined = geoms[0] if len(geoms) == 1 else unary_union(geoms)
    return _shapely_to_geojson(combined)


def _shapely_to_geojson(geom: BaseGeometry) -> dict[str, Any]:
    if geom.is_empty:
        raise ValueError("AOI geometry is empty.")
    mapped = mapping(geom)
    if not isinstance(mapped, dict):
        raise ValueError("Could not convert AOI geometry to GeoJSON.")
    return mapped


def _local_tag(tag: str) -> str:
    return tag.split("}")[-1]


def _parse_kml_coordinates(text: str) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for part in text.strip().replace("\n", " ").split():
        bits = part.split(",")
        if len(bits) < 2:
            continue
        coords.append((float(bits[0]), float(bits[1])))
    return coords


def _geom_from_kml_coords(kind: str, text: str) -> BaseGeometry | None:
    coords = _parse_kml_coordinates(text)
    if not coords:
        return None
    if kind == "Point" or len(coords) == 1:
        return Point(coords[0])
    if kind in {"LineString", "LinearRing"}:
        return LineString(coords)
    ring = coords if coords[0] == coords[-1] else coords + [coords[0]]
    if len(ring) < 4:
        return LineString(coords)
    return Polygon(ring)


def _load_kml(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    geoms: list[BaseGeometry] = []

    for element in root.iter():
        kind = _local_tag(element.tag)
        if kind not in {"Point", "LineString", "LinearRing", "Polygon"}:
            continue
        for child in element.iter():
            if _local_tag(child.tag) != "coordinates" or not child.text:
                continue
            geom = _geom_from_kml_coords(kind, child.text)
            if geom is not None:
                geoms.append(geom)
            break

    if not geoms:
        raise ValueError("No coordinates found in the KML file.")
    combined = geoms[0] if len(geoms) == 1 else unary_union(geoms)
    return _shapely_to_geojson(combined)
