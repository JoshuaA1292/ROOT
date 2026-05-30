from __future__ import annotations

from typing import Any


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_portland_tree(raw: dict[str, Any], index: int = 0) -> dict:
    tree_id = raw.get("tree_id") or raw.get("objectid") or raw.get("inventory_id") or f"portland_{index}"
    lat = _float(raw.get("latitude") or raw.get("lat") or raw.get("y"))
    lng = _float(raw.get("longitude") or raw.get("lon") or raw.get("x"))
    return {
        "_id": f"tree_portland_{tree_id}",
        "source": "portland",
        "species": {
            "common": raw.get("common_name") or raw.get("species") or "Unknown",
            "latin": raw.get("scientific_name") or raw.get("latin_name") or "Unknown",
        },
        "diameter_in": _float(raw.get("dbh") or raw.get("diameter") or raw.get("diameter_in"), 8),
        "health": raw.get("condition") or raw.get("health") or "Unknown",
        "status": raw.get("status") or "Alive",
        "location": {"type": "Point", "coordinates": [lng, lat]},
        "address": raw.get("address") or "",
        "borough": "Portland",
        "census_tract": str(raw.get("census_tract", "")),
        "ecosystem_value_usd_yr": raw.get("ecosystem_value_usd_yr", {}),
        "ej_score": raw.get("ej_score", {"heat_vuln_pct": 50.0, "tract_score": 0.5}),
    }


def normalize_seattle_tree(raw: dict[str, Any], index: int = 0) -> dict:
    tree_id = raw.get("tree_id") or raw.get("objectid") or raw.get("site_id") or f"seattle_{index}"
    lat = _float(raw.get("latitude") or raw.get("lat") or raw.get("y"))
    lng = _float(raw.get("longitude") or raw.get("lon") or raw.get("x"))
    return {
        "_id": f"tree_seattle_{tree_id}",
        "source": "seattle",
        "species": {
            "common": raw.get("common") or raw.get("common_name") or raw.get("species") or "Unknown",
            "latin": raw.get("scientific") or raw.get("scientific_name") or "Unknown",
        },
        "diameter_in": _float(raw.get("dbh") or raw.get("diameter") or raw.get("diameter_in"), 8),
        "health": raw.get("condition") or raw.get("health") or "Unknown",
        "status": raw.get("status") or "Alive",
        "location": {"type": "Point", "coordinates": [lng, lat]},
        "address": raw.get("address") or raw.get("unitdesc") or "",
        "borough": "Seattle",
        "census_tract": str(raw.get("census_tract", "")),
        "ecosystem_value_usd_yr": raw.get("ecosystem_value_usd_yr", {}),
        "ej_score": raw.get("ej_score", {"heat_vuln_pct": 50.0, "tract_score": 0.5}),
    }


ADAPTERS = {
    "portland": normalize_portland_tree,
    "seattle": normalize_seattle_tree,
}


def normalize_city_tree(city: str, raw: dict[str, Any], index: int = 0) -> dict:
    key = city.lower()
    if key not in ADAPTERS:
        raise ValueError(f"Unsupported city tree adapter: {city}")
    return ADAPTERS[key](raw, index)
