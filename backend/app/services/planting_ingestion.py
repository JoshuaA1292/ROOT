from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.db.repositories.planting_records import upsert_planting_records
from app.services.reconciliation import reconcile_developer_ledgers


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def normalize_planting_record(raw: dict[str, Any]) -> dict:
    permit_id = raw.get("permit_id") or raw.get("tree_work_permit_id") or raw.get("permit_number")
    developer_id = raw.get("developer_id") or raw.get("applicant") or raw.get("owner")
    if not permit_id or not developer_id:
        raise ValueError("planting record missing permit_id or developer_id")

    record_id = raw.get("_id") or f"planting_{permit_id}"
    planted = _int(raw.get("planted_count") or raw.get("trees_planted"))
    surviving = _int(raw.get("surviving_3yr_count") or raw.get("trees_alive_3yr") or raw.get("trees_alive"))
    promised = _int(raw.get("promised_count") or raw.get("replacement_tree_count") or planted)

    return {
        "_id": str(record_id),
        "permit_id": str(permit_id),
        "developer_id": str(developer_id).strip().lower().replace(" ", "_"),
        "promised_count": promised,
        "planted_count": planted,
        "surviving_3yr_count": surviving,
        "inspection_year": _int(raw.get("inspection_year") or raw.get("year")),
        "status": raw.get("status") or ("verified" if promised == surviving else "partial_failure"),
        "source": raw.get("source") or "parks_tree_work",
    }


async def ingest_planting_records(
    records: list[dict[str, Any]] | None = None,
    source_url: str | None = None,
    reconcile: bool = True,
) -> dict:
    if records is None:
        url = source_url or settings.parks_tree_work_url
        if not url:
            raise ValueError("No planting records or PARKS_TREE_WORK_URL configured")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            records = response.json()

    normalized = [normalize_planting_record(record) for record in records]
    upserted = await upsert_planting_records(normalized)
    reconciliation = await reconcile_developer_ledgers() if reconcile else None

    return {
        "source": source_url or settings.parks_tree_work_url or "provided_records",
        "records_received": len(records),
        "planting_records_upserted": upserted,
        "record_ids": [record["_id"] for record in normalized],
        "reconciliation": reconciliation,
    }
