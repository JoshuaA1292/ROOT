"""Tests for the Developer Ledger Agent."""
import pytest

from app.agents.developer_ledger_agent import build_snapshot


def test_build_snapshot_computes_delta_against_city_target():
    snapshot = build_snapshot({
        "_id": "dev_atlas_holdings",
        "name": "Atlas Holdings LLC",
        "permits_filed": 3,
        "promised_replacements": 31,
        "verified_surviving": 14,
        "compliance_rate": 0.45,
        "violations": [{"permit_id": "p1", "type": "missing_replacement"}],
    })

    assert snapshot.name == "Atlas Holdings LLC"
    assert snapshot.city_target == pytest.approx(0.85)
    assert snapshot.target_delta == pytest.approx(-0.4)
    assert snapshot.at_risk_replacements == 12
    assert snapshot.violations_count == 1


def test_build_snapshot_handles_missing_developer():
    snapshot = build_snapshot(None, "dev_missing")

    assert snapshot.developer_id == "dev_missing"
    assert snapshot.name == "Unknown Developer"
    assert snapshot.compliance_rate == 0
    assert snapshot.target_delta == pytest.approx(-0.85)
