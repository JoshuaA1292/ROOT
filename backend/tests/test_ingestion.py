"""Tests for permit and Parks planting ingestion."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.permit_ingestion import ingest_permits, normalize_permit_record
from app.services.planting_ingestion import ingest_planting_records, normalize_planting_record


def test_normalize_permit_record_maps_city_fields():
    permit = normalize_permit_record({
        "job_number": "12345",
        "owner_business_name": "Atlas Holdings LLC",
        "pre_filing_date": "2026-05-01",
        "house_street": "487 Atlantic Ave",
        "job_type": "mixed_use",
        "latitude": "40.6862",
        "longitude": "-73.9845",
        "replacement_tree_count": "12",
    })

    assert permit["_id"] == "permit_12345"
    assert permit["developer_id"] == "atlas_holdings_llc"
    assert permit["center"]["coordinates"] == [-73.9845, 40.6862]
    assert permit["promised_replacements"] == 12


@pytest.mark.asyncio
async def test_ingest_permits_upserts_normalized_records():
    with patch("app.services.permit_ingestion.upsert_permits", new=AsyncMock(return_value=1)) as upsert:
        result = await ingest_permits(records=[{"permit_id": "permit_a", "developer_id": "dev_a"}])

    assert result["permits_upserted"] == 1
    assert result["permit_ids"] == ["permit_a"]
    upsert.assert_awaited_once()


def test_normalize_planting_record_maps_parks_fields():
    record = normalize_planting_record({
        "tree_work_permit_id": "permit_1",
        "applicant": "Atlas Holdings LLC",
        "replacement_tree_count": "10",
        "trees_planted": "8",
        "trees_alive": "5",
        "year": "2026",
    })

    assert record["_id"] == "planting_permit_1"
    assert record["developer_id"] == "atlas_holdings_llc"
    assert record["promised_count"] == 10
    assert record["surviving_3yr_count"] == 5


@pytest.mark.asyncio
async def test_ingest_planting_records_upserts_and_reconciles():
    with (
        patch("app.services.planting_ingestion.upsert_planting_records", new=AsyncMock(return_value=1)),
        patch("app.services.planting_ingestion.reconcile_developer_ledgers", new=AsyncMock(return_value={"developers_reconciled": 1})),
    ):
        result = await ingest_planting_records(
            records=[{"permit_id": "p1", "developer_id": "dev_a", "planted_count": 1}],
            reconcile=True,
        )

    assert result["planting_records_upserted"] == 1
    assert result["reconciliation"]["developers_reconciled"] == 1
