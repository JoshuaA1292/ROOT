"""
Intervention Strategy Engine — pure Python, no LLM required.

Derives a recommended action, confidence level, best argument, and
enforceable conditions from the coalition + developer + precedent data
already computed by the pipeline.  Runs in the orchestrator after all
four agent calls complete, before the briefing is saved.
"""
from __future__ import annotations

from typing import Any


_RISK_TIERS = {
    (0.0, 0.40): "critical",
    (0.40, 0.60): "high",
    (0.60, 0.85): "elevated",
    (0.85, 1.01): "compliant",
}


def _dev_risk_tier(rate: float) -> str:
    for (lo, hi), label in _RISK_TIERS.items():
        if lo <= rate < hi:
            return label
    return "compliant"


def build_intervention_strategy(
    coalition: dict[str, Any],
    developer: dict[str, Any],
    precedents: list[dict[str, Any]],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Returns a structured intervention strategy dict suitable for storage
    in the briefing document and display in the Case File UI.
    """
    compliance_rate: float = developer.get("compliance_rate", 1.0)
    tree_count: int = coalition.get("tree_count", 0)
    total_usd: float = coalition.get("total_ecosystem_usd_yr", 0)
    ej_tier: str = coalition.get("ej_tier", "Low")
    heat_residents: int = coalition.get("heat_vulnerable_residents", 0)
    linked_entities: list[str] = developer.get("linked_entities", [])
    target_delta: float = developer.get("target_delta", 0)
    violations_count: int = developer.get("violations_count", 0)
    promised: int = developer.get("promised_replacements", 0)
    verified: int = developer.get("verified_surviving", 0)
    at_risk_replacements: int = developer.get(
        "at_risk_replacements",
        max(round(promised * 0.85) - verified, 0),
    )

    tier = _dev_risk_tier(compliance_rate)
    exposure_score = min(
        100,
        round(
            (max(0.0, 0.85 - compliance_rate) * 55)
            + min(violations_count * 8, 24)
            + min(at_risk_replacements * 2.5, 18)
            + min(tree_count * 0.9, 14)
            + (8 if ej_tier == "High" else 0)
        ),
    )

    # ── Recommended action ──────────────────────────────────────────────────
    if compliance_rate < 0.40 or violations_count >= 3:
        recommended_action = "ESCALATE — DENY OR REQUIRE MAJOR CONDITIONS"
        confidence = "High"
    elif compliance_rate < 0.60 or (ej_tier == "High" and tree_count >= 10):
        recommended_action = "ESCALATE WITH ENFORCEABLE CONDITIONS"
        confidence = "High"
    elif compliance_rate < 0.85:
        recommended_action = "FILE COMMENT WITH STANDARD CONDITIONS"
        confidence = "Medium"
    else:
        recommended_action = "APPROVE WITH MONITORING"
        confidence = "Low"

    # ── Best argument ────────────────────────────────────────────────────────
    if compliance_rate < 0.85 and violations_count > 0:
        best_argument = "developer_compliance_history"
        best_argument_rationale = (
            f"{developer.get('name', 'The developer')} has a {round(compliance_rate*100)}% "
            f"verified replacement survival rate — {round(abs(target_delta)*100)} points "
            f"below the city's 85% benchmark, with {violations_count} documented violation(s). "
            f"This directly challenges whether the replacement promise is credible."
        )
    elif ej_tier == "High" and heat_residents > 0:
        best_argument = "ej_disparity_and_heat_vulnerability"
        best_argument_rationale = (
            f"The affected census tract is in the EJ High tier with {heat_residents:,} "
            f"heat-vulnerable residents. Canopy removal here has a disproportionate public "
            f"health cost that satisfies the heightened scrutiny standard under PlaNYC."
        )
    elif total_usd >= 5000:
        best_argument = "ecosystem_valuation"
        best_argument_rationale = (
            f"The threatened coalition provides ${total_usd:,.0f}/year in quantified "
            f"ecosystem services (i-Tree methodology). This is a measurable, irreplaceable "
            f"public asset loss that the application does not adequately address."
        )
    else:
        best_argument = "replacement_survival_rate"
        best_argument_rationale = (
            "Standard replacement conditions apply given the developer's compliance history."
        )

    # ── Precedent signal ─────────────────────────────────────────────────────
    precedent_signal: dict[str, Any] = {}
    if precedents:
        top = precedents[0]
        precedent_signal = {
            "title": top.get("title", ""),
            "outcome": top.get("outcome", ""),
            "year": top.get("year", 0),
            "similarity_score": top.get("similarity_score", 0),
            "arguments_used": top.get("arguments_used", []),
        }

    # ── Requested conditions ─────────────────────────────────────────────────
    bond_pct = 200 if tier == "critical" else 150
    surety_usd = max(5000, round(total_usd * bond_pct / 100 / 100) * 100)

    conditions = [
        f"Performance bond of ${surety_usd:,} ({bond_pct}% of estimated replacement cost) "
        f"payable to NYC Parks ForMS escrow",
        "Independent arborist inspection and photo-documented survival report at 12, 36, and 60 months",
        "GPS-tagged planting records submitted to NYC Parks ForMS within 30 days of installation",
        "Species diversity requirement: minimum 3 approved native species in replacement plan",
        "Public survival status updates attached to any future permit applications by this developer",
    ]
    if linked_entities:
        conditions.append(
            f"All linked entities ({', '.join(linked_entities)}) disclosed and included in "
            f"compliance tracking for this permit"
        )

    # ── Why this recommendation ──────────────────────────────────────────────
    reasons: list[str] = []
    if compliance_rate < 0.85:
        reasons.append(
            f"{developer.get('name', 'Developer')} has a {round(compliance_rate*100)}% "
            f"replacement survival rate, {round(abs(target_delta)*100)} pts below the city target"
        )
    if ej_tier == "High":
        reasons.append(
            f"High EJ burden: {heat_residents:,} heat-vulnerable residents in the affected tract"
        )
    if total_usd >= 1000:
        reasons.append(
            f"Threatened coalition provides ${total_usd:,.0f}/yr in ecosystem services"
        )
    if precedent_signal.get("outcome") in ("denied", "permit_modified"):
        reasons.append(
            f"Similar case ({precedent_signal.get('title', '')}) was "
            f"{precedent_signal.get('outcome', '').replace('_', ' ')} in "
            f"{precedent_signal.get('year', '')}"
        )
    if violations_count:
        reasons.append(f"{violations_count} documented violation(s) on prior permits")

    return {
        "recommended_action": recommended_action,
        "confidence": confidence,
        "developer_risk_tier": tier,
        "cumulative_exposure_score": exposure_score,
        "best_argument": best_argument,
        "best_argument_rationale": best_argument_rationale,
        "reasons": reasons,
        "requested_conditions": conditions,
        "precedent_signal": precedent_signal,
    }


def build_evidence_board(
    coalition: dict[str, Any],
    developer: dict[str, Any],
    precedents: list[dict[str, Any]],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compact structured evidence for the Evidence Board UI tile."""
    top_precedent = precedents[0] if precedents else {}
    return {
        "developer": {
            "name": developer.get("name", ""),
            "compliance_rate": developer.get("compliance_rate", 0),
            "city_target": developer.get("city_target", 0.85),
            "permits_filed": developer.get("permits_filed", 0),
            "promised_replacements": developer.get("promised_replacements", 0),
            "verified_surviving": developer.get("verified_surviving", 0),
            "violations_count": developer.get("violations_count", 0),
            "linked_entity_count": len(developer.get("linked_entities", [])),
            "at_risk_replacements": developer.get("at_risk_replacements", 0),
            "cumulative_exposure_score": min(
                100,
                round(
                    (max(0.0, 0.85 - developer.get("compliance_rate", 0)) * 55)
                    + min(developer.get("violations_count", 0) * 8, 24)
                    + min(developer.get("at_risk_replacements", 0) * 2.5, 18)
                    + min(coalition.get("tree_count", 0) * 0.9, 14)
                    + (8 if coalition.get("ej_tier") == "High" else 0)
                ),
            ),
        },
        "coalition": {
            "tree_count": coalition.get("tree_count", 0),
            "canopy_sqft": coalition.get("canopy_sqft", 0),
            "stormwater_gal_yr": coalition.get("stormwater_gal_yr", 0),
            "total_ecosystem_usd_yr": coalition.get("total_ecosystem_usd_yr", 0),
            "ej_tier": coalition.get("ej_tier", "Low"),
            "heat_vulnerable_residents": coalition.get("heat_vulnerable_residents", 0),
        },
        "top_precedent": {
            "title": top_precedent.get("title", ""),
            "outcome": top_precedent.get("outcome", ""),
            "year": top_precedent.get("year", 0),
            "similarity_score": top_precedent.get("similarity_score", 0),
            "arguments_used": top_precedent.get("arguments_used", []),
        } if top_precedent else None,
        "policy_count": len(policies),
        "policy_titles": [p.get("title", "") for p in policies[:4]],
    }
