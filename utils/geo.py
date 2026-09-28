"""Ressources cartographiques (limites administratives du Togo).

Seule la géométrie régionale (5 polygones) est disponible de façon fiable.
Aucune frontière de préfecture, de commune ou de canton n'est inventée : le
zoom sur ces échelons s'appuie sur les coordonnées réelles des communes
(``lon_c``/``lat_c``, table_analytique_communes) déjà validées en amont.
"""
from __future__ import annotations

import json
from functools import lru_cache

from . import config as C

DEFAULT_GEOJSON = C.ASSETS_DIR / "geo" / "togo_regions.geojson"


@lru_cache(maxsize=1)
def load_regions_geojson() -> dict:
    return json.loads(DEFAULT_GEOJSON.read_text(encoding="utf-8"))


def _ring_bounds(geometry: dict) -> tuple[float, float, float, float]:
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    xs: list[float] = []
    ys: list[float] = []
    for polygon in polygons:
        for ring in polygon:
            xs += [pt[0] for pt in ring]
            ys += [pt[1] for pt in ring]
    return min(xs), max(xs), min(ys), max(ys)


@lru_cache(maxsize=1)
def region_polygon_bounds() -> dict[str, tuple[float, float, float, float]]:
    """(lon_min, lon_max, lat_min, lat_max) réel par région, à partir du GeoJSON."""
    geo = load_regions_geojson()
    out: dict[str, tuple[float, float, float, float]] = {}
    for feature in geo["features"]:
        name = C.REGION_GEO_ALIAS.get(feature["properties"]["region"], feature["properties"]["region"])
        out[name] = _ring_bounds(feature["geometry"])
    return out


def national_bounds() -> tuple[float, float, float, float]:
    bounds = list(region_polygon_bounds().values())
    x0 = min(b[0] for b in bounds)
    x1 = max(b[1] for b in bounds)
    y0 = min(b[2] for b in bounds)
    y1 = max(b[3] for b in bounds)
    # Inclut le point de Grand Lomé (hors polygone).
    lat, lon = C.GEO_POINTS["Grand Lomé"]
    x0, x1 = min(x0, lon), max(x1, lon)
    y0, y1 = min(y0, lat), max(y1, lat)
    return x0, x1, y0, y1
