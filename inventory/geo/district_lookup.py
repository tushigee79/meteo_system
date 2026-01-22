# inventory/geo/district_lookup.py
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any

from shapely.geometry import shape, Point

# Path in your project: BASE_DIR/static/data/ub_districts.geojson
# We keep it relative so it works on Windows too.
UB_GEOJSON_REL = Path("static") / "data" / "ub_districts.geojson"


@lru_cache(maxsize=1)
def _load_features(base_dir: Path):
    fp = base_dir / UB_GEOJSON_REL
    data = json.loads(fp.read_text(encoding="utf-8"))
    feats = data.get("features", [])
    parsed = []
    for ft in feats:
        geom = shape(ft["geometry"])
        props = ft.get("properties", {})
        parsed.append((geom, props))
    return parsed


def lookup_ub_district(lon: float, lat: float, base_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Returns district properties if (lon,lat) falls inside a UB district polygon.
    base_dir should be your Django BASE_DIR (Path object).
    """
    pt = Point(float(lon), float(lat))
    for geom, props in _load_features(base_dir):
        if geom.contains(pt):
            return props
    return None