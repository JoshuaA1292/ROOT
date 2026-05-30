"""Tests for coalition_agent — mocked DB to avoid Atlas dependency."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.coalition_agent import run


MOCK_TREES = [
    {
        "_id": "tree_001",
        "diameter_in": 14,
        "ecosystem_value_usd_yr": {
            "stormwater_gal": 1428, "stormwater_usd": 12.57,
            "co2_lbs": 214.2, "co2_usd": 4.50,
            "cooling_kwh": 86.8, "cooling_usd": 12.15,
            "air_quality_usd": 5.32, "total_usd": 34.54
        },
        "ej_score": {"heat_vuln_pct": 85.0, "tract_score": 0.85},
    },
    {
        "_id": "tree_002",
        "diameter_in": 20,
        "ecosystem_value_usd_yr": {
            "stormwater_gal": 2040, "stormwater_usd": 17.95,
            "co2_lbs": 306.0, "co2_usd": 6.43,
            "cooling_kwh": 124.0, "cooling_usd": 17.36,
            "air_quality_usd": 7.60, "total_usd": 49.34
        },
        "ej_score": {"heat_vuln_pct": 78.0, "tract_score": 0.78},
    },
]


@pytest.mark.asyncio
async def test_coalition_returns_aggregated_values():
    with (
        patch("app.agents.coalition_agent.get_trees_in_radius", new=AsyncMock(return_value=MOCK_TREES)),
        patch("app.agents.coalition_agent.update_permit_threatened_trees", new=AsyncMock()),
    ):
        result = await run("permit_test", -73.98, 40.69, 80)

    assert result.tree_count == 2
    assert result.total_ecosystem_usd_yr == pytest.approx(83.88, abs=0.1)
    assert result.ej_tier == "High"  # avg 81.5 > 66
    assert "tree_001" in result.tree_ids
    assert "tree_002" in result.tree_ids


@pytest.mark.asyncio
async def test_coalition_empty_radius():
    with (
        patch("app.agents.coalition_agent.get_trees_in_radius", new=AsyncMock(return_value=[])),
        patch("app.agents.coalition_agent.update_permit_threatened_trees", new=AsyncMock()),
    ):
        result = await run("permit_test", -73.98, 40.69, 80)

    assert result.tree_count == 0
    assert result.total_ecosystem_usd_yr == 0
    assert result.ej_tier == "Low"


@pytest.mark.asyncio
async def test_coalition_ej_tier_medium():
    mid_ej_trees = [
        {**MOCK_TREES[0], "ej_score": {"heat_vuln_pct": 50.0, "tract_score": 0.50}},
    ]
    with (
        patch("app.agents.coalition_agent.get_trees_in_radius", new=AsyncMock(return_value=mid_ej_trees)),
        patch("app.agents.coalition_agent.update_permit_threatened_trees", new=AsyncMock()),
    ):
        result = await run("permit_test", -73.98, 40.69, 80)

    assert result.ej_tier == "Medium"
