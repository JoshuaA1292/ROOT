from __future__ import annotations

import httpx

from app.config import settings
from app.db.repositories.ingestion_runs import record_ingestion_run
from app.db.repositories.trees import upsert_trees
from app.services.tree_adapters import normalize_city_tree


def city_source_url(city: str) -> str:
    key = city.lower()
    if key == "portland":
        return settings.portland_tree_inventory_url
    if key == "seattle":
        return settings.seattle_tree_inventory_url
    return ""


async def ingest_city_trees(city: str, records: list[dict] | None = None, source_url: str | None = None) -> dict:
    source = source_url or city_source_url(city)
    if records is None:
        if not source:
            raise ValueError(f"No records or source URL configured for {city}")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(source)
            response.raise_for_status()
            records = response.json()

    normalized = [normalize_city_tree(city, record, index) for index, record in enumerate(records)]
    upserted = await upsert_trees(normalized)
    result = {
        "city": city.lower(),
        "source": source or "provided_records",
        "records_received": len(records),
        "trees_upserted": upserted,
        "tree_ids": [tree["_id"] for tree in normalized],
    }
    result["ingestion_run_id"] = await record_ingestion_run("tree_inventory", result["source"], result)
    return result
