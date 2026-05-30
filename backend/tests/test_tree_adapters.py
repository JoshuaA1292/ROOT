"""Tests for multi-city tree adapters."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.tree_adapters import normalize_city_tree, normalize_portland_tree, normalize_seattle_tree
from app.services.tree_ingestion import ingest_city_trees


def test_normalize_portland_tree_maps_fields():
    tree = normalize_portland_tree({
        "objectid": "42",
        "common_name": "Bigleaf Maple",
        "scientific_name": "Acer macrophyllum",
        "dbh": "12",
        "latitude": "45.52",
        "longitude": "-122.67",
    })

    assert tree["_id"] == "tree_portland_42"
    assert tree["species"]["common"] == "Bigleaf Maple"
    assert tree["location"]["coordinates"] == [-122.67, 45.52]


def test_normalize_seattle_tree_maps_fields():
    tree = normalize_seattle_tree({
        "site_id": "99",
        "common": "Red Maple",
        "scientific": "Acer rubrum",
        "diameter": "9",
        "lat": "47.61",
        "lon": "-122.33",
    })

    assert tree["_id"] == "tree_seattle_99"
    assert tree["species"]["latin"] == "Acer rubrum"


def test_normalize_city_tree_rejects_unsupported_city():
    with pytest.raises(ValueError):
        normalize_city_tree("boston", {})


@pytest.mark.asyncio
async def test_ingest_city_trees_upserts_records():
    with (
        patch("app.services.tree_ingestion.upsert_trees", new=AsyncMock(return_value=1)),
        patch("app.services.tree_ingestion.record_ingestion_run", new=AsyncMock(return_value="ingest_1")),
    ):
        result = await ingest_city_trees("portland", records=[{"objectid": "1"}])

    assert result["trees_upserted"] == 1
    assert result["ingestion_run_id"] == "ingest_1"
