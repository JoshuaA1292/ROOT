from app.agents import polish_agent
from app.models.briefing import CoalitionSummary, DeveloperSnapshot, PolicyRef


def test_polish_agent_replaces_truncated_draft():
    coalition = CoalitionSummary(
        tree_count=4,
        canopy_sqft=752,
        stormwater_gal_yr=6398,
        co2_lbs_lifetime=47985,
        cooling_usd_yr=54.45,
        total_ecosystem_usd_yr=154.73,
        ej_tier="High",
        heat_vulnerable_residents=180,
        tree_ids=["t1", "t2", "t3", "t4"],
    )
    developer = DeveloperSnapshot(
        developer_id="dev_atlas",
        name="Atlas Holdings LLC",
        compliance_rate=0.45,
        city_target=0.85,
        target_delta=-0.40,
        permits_filed=3,
        promised_replacements=31,
        verified_surviving=14,
        violations_count=3,
        at_risk_replacements=12,
    )
    policy = PolicyRef(
        id="policy_canopy",
        title="Urban Forest Plan",
        section="Canopy Target",
        text_excerpt="The city seeks expanded canopy coverage and heat-risk reduction.",
        matched_tags=["canopy"],
    )

    result = polish_agent.run(
        "### 1. Opening Statement\nThis starts well.\n\n### 5. Policy Contradictions\nThe OneNYC 2050 Urban Forest Strategy and the",
        {
            "_id": "permit_2026_0184",
            "address": "487 Atlantic Ave, Brooklyn, NY 11217",
            "project_type": "mixed_use_tower",
            "stated_reason": "foundation work",
            "promised_replacements": 12,
        },
        coalition,
        developer,
        [],
        [policy],
    )

    assert "### 1. Opening Statement" not in result
    assert "### 7. Closing" not in result
    assert "### Citations & Data Sources" not in result
    assert "CITATIONS & DATA SOURCES" in result
    assert "OPENING STATEMENT" not in result
    assert "ECOSYSTEM IMPACT" not in result
    assert "CLOSING" not in result
    assert result.rstrip().endswith(".")
    assert "Atlas Holdings LLC" in result


def test_polish_agent_rejects_long_but_weak_draft():
    coalition = CoalitionSummary(
        tree_count=1,
        canopy_sqft=100,
        stormwater_gal_yr=1000,
        co2_lbs_lifetime=5000,
        cooling_usd_yr=25,
        total_ecosystem_usd_yr=75,
        ej_tier="Medium",
        heat_vulnerable_residents=12,
        tree_ids=["t1"],
    )
    developer = DeveloperSnapshot(
        developer_id="dev",
        name="Weak Draft LLC",
        compliance_rate=0.5,
        city_target=0.85,
        target_delta=-0.35,
        permits_filed=2,
        promised_replacements=10,
        verified_surviving=5,
        violations_count=1,
        at_risk_replacements=4,
    )
    weak = (
        "This public comment is important. " * 130
        + "\n\nCITATIONS & DATA SOURCES\n- ROOT data."
    )

    result = polish_agent.run(
        weak,
        {
            "_id": "permit_weak",
            "address": "10 Test Ave",
            "project_type": "residential",
            "stated_reason": "construction access",
            "promised_replacements": 3,
        },
        coalition,
        developer,
        [],
        [],
    )

    assert "Weak Draft LLC" in result
    assert result.lower().count("require ") >= 3
    assert "stormwater" in result.lower()
    assert "verification" in result.lower()
