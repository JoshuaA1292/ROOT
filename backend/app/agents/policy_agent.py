"""
Policy Agent: selects city policy references that are relevant to a permit's
coalition impact and developer compliance record.
"""
from __future__ import annotations

from app.db.repositories.city_policies import list_city_policies
from app.models.briefing import CoalitionSummary, DeveloperSnapshot, PolicyRef


def _tags_for_context(coalition: CoalitionSummary, developer: DeveloperSnapshot) -> set[str]:
    tags = {"replacement_ratio", "diameter_threshold", "commissioner_approval"}

    if coalition.canopy_sqft > 0:
        tags.update({"canopy_target", "30_percent_by_2035"})

    if coalition.ej_tier == "High":
        tags.update({
            "heat_vulnerability",
            "priority_preservation",
            "environmental_review",
            "ej_score",
            "heat_vulnerable_neighborhoods",
        })

    if coalition.co2_lbs_lifetime > 0:
        tags.update({"carbon_sequestration", "co2_offset", "climate_mobilization"})

    if developer.compliance_rate < developer.city_target:
        tags.update({"survival_rate", "performance_bond", "arborist_verification"})

    return tags


def select_relevant_policies(
    policies: list[dict],
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    limit: int = 4,
) -> list[PolicyRef]:
    context_tags = _tags_for_context(coalition, developer)
    scored: list[tuple[int, dict, list[str]]] = []

    for policy in policies:
        matched = sorted(context_tags.intersection(set(policy.get("tags", []))))
        if matched:
            scored.append((len(matched), policy, matched))

    scored.sort(key=lambda item: (-item[0], item[1].get("title", "")))

    return [
        PolicyRef(
            id=str(policy.get("_id", "")),
            title=policy.get("title", ""),
            section=policy.get("section", ""),
            text_excerpt=policy.get("text_excerpt", ""),
            matched_tags=matched,
        )
        for _, policy, matched in scored[:limit]
    ]


async def run(
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    jurisdiction: str = "NYC",
    limit: int = 4,
) -> list[PolicyRef]:
    policies = await list_city_policies(jurisdiction)
    return select_relevant_policies(policies, coalition, developer, limit)
