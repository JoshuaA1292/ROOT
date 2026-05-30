"""Tests for the ADK tool functions (no actual Google credentials needed)."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.adk_agent import (
    get_coalition_impact,
    get_developer_ledger,
    get_policy_references,
    search_relevant_precedents,
)
from app.models.briefing import CoalitionSummary


MOCK_PERMIT = {
    "_id": "permit_2026_0184",
    "developer_id": "dev_atlas_holdings",
    "address": "487 Atlantic Ave, Brooklyn",
    "project_type": "mixed_use_tower",
    "removal_radius_m": 80,
    "center": {"type": "Point", "coordinates": [-73.9845, 40.6862]},
    "stated_reason": "Foundation work",
    "promised_replacements": 12,
    "comment_deadline": "2026-06-25",
    "status": "open_for_comment",
    "threatened_tree_ids": [],
}

MOCK_DEV = {
    "_id": "dev_atlas_holdings",
    "name": "Atlas Holdings LLC",
    "permits_filed": 3,
    "promised_replacements": 31,
    "verified_surviving": 14,
    "compliance_rate": 0.45,
    "violations": [{"permit_id": "p1", "type": "missing_replacement", "count": 3, "year": 2022}],
    "linked_entities": [],
}

MOCK_COALITION = CoalitionSummary(
    tree_count=14,
    canopy_sqft=2800,
    stormwater_gal_yr=87400,
    co2_lbs_lifetime=152600,
    cooling_usd_yr=1820,
    total_ecosystem_usd_yr=4200,
    ej_tier="High",
    heat_vulnerable_residents=340,
    tree_ids=["tree_001"] * 14,
)


@pytest.mark.asyncio
async def test_get_coalition_impact_returns_dict():
    with (
        patch("app.agents.adk_agent.get_permit_by_id", new=AsyncMock(return_value=MOCK_PERMIT)),
        patch("app.agents.adk_agent.coalition_agent.run", new=AsyncMock(return_value=MOCK_COALITION)),
    ):
        result = await get_coalition_impact("permit_2026_0184")

    assert result["tree_count"] == 14
    assert result["ej_tier"] == "High"
    assert result["total_ecosystem_usd_yr"] == pytest.approx(4200.0)


@pytest.mark.asyncio
async def test_get_coalition_impact_missing_permit():
    with patch("app.agents.adk_agent.get_permit_by_id", new=AsyncMock(return_value=None)):
        result = await get_coalition_impact("nonexistent")

    assert "error" in result


@pytest.mark.asyncio
async def test_get_developer_ledger_returns_compliance():
    with (
        patch("app.agents.adk_agent.get_permit_by_id", new=AsyncMock(return_value=MOCK_PERMIT)),
        patch("app.agents.developer_ledger_agent.get_developer_by_id", new=AsyncMock(return_value=MOCK_DEV)),
    ):
        result = await get_developer_ledger("permit_2026_0184")

    assert result["name"] == "Atlas Holdings LLC"
    assert result["compliance_rate"] == pytest.approx(0.45)
    assert result["city_target"] == pytest.approx(0.85)
    assert result["target_delta"] == pytest.approx(-0.4)


@pytest.mark.asyncio
async def test_get_developer_ledger_unknown_dev():
    with (
        patch("app.agents.adk_agent.get_permit_by_id", new=AsyncMock(return_value=MOCK_PERMIT)),
        patch("app.agents.developer_ledger_agent.get_developer_by_id", new=AsyncMock(return_value=None)),
    ):
        result = await get_developer_ledger("permit_2026_0184")

    assert "Unknown" in result["name"]
    assert result["compliance_rate"] == 0


@pytest.mark.asyncio
async def test_search_relevant_precedents_returns_list():
    mock_results = [
        {
            "_id": "prec_0001",
            "title": "Brooklyn Heights 2022",
            "outcome": "permit_modified",
            "year": 2022,
            "score": 0.91,
            "arguments_used": ["stormwater_load"],
            "comment_text": "This is a test comment.",
        }
    ]

    async def fake_vector_search(embedding, top_k):
        return mock_results

    with (
        patch("app.agents.adk_agent.embed_text", return_value=[0.1] * 768),
        patch("app.agents.adk_agent.vector_search_precedents", side_effect=fake_vector_search),
    ):
        result = await search_relevant_precedents("mixed-use tower removing 14 trees in Brooklyn, High EJ")

    assert len(result) == 1
    assert result[0]["title"] == "Brooklyn Heights 2022"
    assert result[0]["similarity_score"] == pytest.approx(0.91)


@pytest.mark.asyncio
async def test_get_policy_references_returns_matches():
    policy_result = [{
        "id": "policy_parks_rule_1_04",
        "title": "NYC Parks Rule 1-04",
        "section": "56 RCNY § 1-04",
        "text_excerpt": "Low survival rates may require a bond.",
        "matched_tags": ["survival_rate"],
    }]

    with patch("app.agents.adk_agent.policy_agent.run", new=AsyncMock(return_value=[
        type("Policy", (), {"model_dump": lambda self: policy_result[0]})()
    ])):
        result = await get_policy_references(
            MOCK_COALITION.model_dump(),
            {
                "developer_id": "dev_atlas_holdings",
                "name": "Atlas Holdings LLC",
                "compliance_rate": 0.45,
                "city_target": 0.85,
                "target_delta": -0.4,
                "permits_filed": 3,
                "promised_replacements": 31,
                "verified_surviving": 14,
                "violations_count": 1,
                "at_risk_replacements": 12,
            },
        )

    assert result == policy_result
