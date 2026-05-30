from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from app.config import settings
from app.db.repositories.permits import upsert_permits


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_permit_record(raw: dict[str, Any]) -> dict:
    permit_id = (
        raw.get("_id")
        or raw.get("permit_id")
        or raw.get("job__")
        or raw.get("job_number")
        or raw.get("dob_job_number")
    )
    if not permit_id:
        raise ValueError("permit record missing id")

    developer = raw.get("developer_id") or raw.get("owner_business_name") or raw.get("applicant_business_name")
    lat = _float(raw.get("latitude") or raw.get("lat") or raw.get("gis_latitude"), 40.7128)
    lng = _float(raw.get("longitude") or raw.get("lng") or raw.get("gis_longitude"), -74.0060)
    promised = int(_float(raw.get("promised_replacements") or raw.get("replacement_tree_count"), 0))

    filed_date = raw.get("filed_date") or raw.get("pre_filing_date") or date.today().isoformat()
    comment_deadline = raw.get("comment_deadline") or (
        date.fromisoformat(str(filed_date)[:10]) + timedelta(days=45)
    ).isoformat()

    return {
        "_id": f"permit_{permit_id}".replace(" ", "_").lower()
        if not str(permit_id).startswith("permit_")
        else str(permit_id),
        "developer_id": str(developer or "unknown_developer").strip().lower().replace(" ", "_"),
        "filed_date": str(filed_date)[:10],
        "address": raw.get("address") or raw.get("house_street") or raw.get("location") or "Unknown address",
        "project_type": raw.get("project_type") or raw.get("job_type") or "tree_work",
        "removal_radius_m": _float(raw.get("removal_radius_m") or raw.get("impact_radius_m"), 50),
        "center": {"type": "Point", "coordinates": [lng, lat]},
        "stated_reason": raw.get("stated_reason") or raw.get("work_type") or "Tree work permit filing",
        "promised_replacements": promised,
        "comment_deadline": comment_deadline,
        "status": raw.get("status") or "open_for_comment",
        "threatened_tree_ids": raw.get("threatened_tree_ids", []),
        "source": raw.get("source") or "nyc_dob",
    }


async def ingest_permits(records: list[dict[str, Any]] | None = None, source_url: str | None = None) -> dict:
    if records is None:
        url = source_url or settings.nyc_dob_permit_url
        if not url:
            raise ValueError("No permit records or NYC_DOB_PERMIT_URL configured")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            records = response.json()

    normalized = [normalize_permit_record(record) for record in records]
    upserted = await upsert_permits(normalized)
    return {
        "source": source_url or settings.nyc_dob_permit_url or "provided_records",
        "records_received": len(records),
        "permits_upserted": upserted,
        "permit_ids": [permit["_id"] for permit in normalized],
    }
