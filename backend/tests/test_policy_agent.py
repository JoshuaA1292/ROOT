"""Tests for policy reference selection."""
import pytest

from app.agents.policy_agent import select_relevant_policies
from app.models.briefing import CoalitionSummary, DeveloperSnapshot


def test_select_relevant_policies_matches_canopy_heat_and_survival_tags():
    coalition = CoalitionSummary(
        tree_count=14,
        canopy_sqft=2800,
        stormwater_gal_yr=87400,
        co2_lbs_lifetime=152600,
        cooling_usd_yr=1820,
        total_ecosystem_usd_yr=4200,
        ej_tier="High",
        heat_vulnerable_residents=340,
        tree_ids=["tree_001"],
    )
    developer = DeveloperSnapshot(
        developer_id="dev_atlas_holdings",
        name="Atlas Holdings LLC",
        compliance_rate=0.45,
        city_target=0.85,
        target_delta=-0.4,
        permits_filed=3,
        promised_replacements=31,
        verified_surviving=14,
        violations_count=1,
        at_risk_replacements=12,
    )
    policies = [
        {
            "_id": "policy_heat",
            "title": "Heat Plan",
            "section": "Chapter 4",
            "text_excerpt": "Heat-vulnerable tracts require enhanced review.",
            "tags": ["heat_vulnerability", "environmental_review"],
        },
        {
            "_id": "policy_survival",
            "title": "Street Tree Standards",
            "section": "56 RCNY 1-04",
            "text_excerpt": "Low survival rates may require a bond.",
            "tags": ["survival_rate", "performance_bond"],
        },
    ]

    result = select_relevant_policies(policies, coalition, developer)

    assert [p.id for p in result] == ["policy_heat", "policy_survival"]
    assert result[0].matched_tags == ["environmental_review", "heat_vulnerability"]


def test_select_relevant_policies_returns_empty_when_no_tags_match():
    coalition = CoalitionSummary(
        tree_count=0,
        canopy_sqft=0,
        stormwater_gal_yr=0,
        co2_lbs_lifetime=0,
        cooling_usd_yr=0,
        total_ecosystem_usd_yr=0,
        ej_tier="Low",
        heat_vulnerable_residents=0,
        tree_ids=[],
    )
    developer = DeveloperSnapshot(
        developer_id="dev_ok",
        name="Compliant Builder",
        compliance_rate=0.95,
        permits_filed=2,
        promised_replacements=10,
        verified_surviving=10,
        violations_count=0,
    )

    assert select_relevant_policies([], coalition, developer) == []
