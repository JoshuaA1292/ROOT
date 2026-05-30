"""Tests for replacement planting reconciliation."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.reconciliation import build_ledger_from_records, reconcile_developer_ledgers


def test_build_ledger_from_records_computes_survival_and_violations():
    ledgers = build_ledger_from_records([
        {
            "permit_id": "permit_1",
            "developer_id": "dev_a",
            "promised_count": 10,
            "planted_count": 8,
            "surviving_3yr_count": 5,
            "inspection_year": 2025,
            "status": "partial_failure",
        },
        {
            "permit_id": "permit_2",
            "developer_id": "dev_a",
            "promised_count": 5,
            "planted_count": 5,
            "surviving_3yr_count": 5,
            "inspection_year": 2026,
            "status": "verified",
        },
    ])

    ledger = ledgers["dev_a"]
    assert ledger["permits_filed"] == 2
    assert ledger["promised_replacements"] == 15
    assert ledger["verified_planted"] == 13
    assert ledger["verified_surviving"] == 10
    assert ledger["compliance_rate"] == pytest.approx(0.6667)
    assert {v["type"] for v in ledger["violations"]} == {
        "missing_replacement",
        "replacement_mortality",
    }


@pytest.mark.asyncio
async def test_reconcile_developer_ledgers_persists_each_ledger():
    records = [
        {
            "permit_id": "permit_1",
            "developer_id": "dev_a",
            "promised_count": 10,
            "planted_count": 8,
            "surviving_3yr_count": 5,
            "inspection_year": 2025,
            "status": "partial_failure",
        }
    ]

    with (
        patch("app.services.reconciliation.list_planting_records", new=AsyncMock(return_value=records)),
        patch("app.services.reconciliation.upsert_developer_ledger", new=AsyncMock()) as upsert,
    ):
        result = await reconcile_developer_ledgers("dev_a")

    assert result["developers_reconciled"] == 1
    assert result["records_processed"] == 1
    upsert.assert_awaited_once()
