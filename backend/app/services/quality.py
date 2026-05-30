REQUIRED_SECTIONS = [
    "Opening Statement",
    "Ecosystem Impact",
    "Developer Compliance",
    "Policy",
    "Requested Conditions",
]

from app.db.repositories.briefings import get_briefing_by_id
from app.db.repositories.quality_alerts import create_quality_alert


def score_briefing_quality(briefing: dict) -> dict:
    draft = briefing.get("draft_comment", "") or ""
    citations = briefing.get("citations", []) or []
    policy_refs = briefing.get("policy_refs", []) or []
    precedent_refs = briefing.get("precedent_refs", []) or []

    checks = {
        "has_draft": bool(draft.strip()),
        "has_citations": len(citations) > 0,
        "has_policy_refs": len(policy_refs) > 0,
        "has_precedents": len(precedent_refs) > 0,
        "has_requested_conditions": "Requested Conditions" in draft or "Requested conditions" in draft,
    }
    section_hits = sum(1 for section in REQUIRED_SECTIONS if section.lower() in draft.lower())
    raw_score = (
        20 * int(checks["has_draft"])
        + 15 * int(checks["has_citations"])
        + 20 * int(checks["has_policy_refs"])
        + 15 * int(checks["has_precedents"])
        + 10 * int(checks["has_requested_conditions"])
        + min(section_hits * 4, 20)
    )

    return {
        "score": min(raw_score, 100),
        "checks": checks,
        "section_hits": section_hits,
        "word_count": len(draft.split()),
    }


async def evaluate_briefing_quality(briefing_id: str, min_score: int = 75) -> dict:
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise ValueError(f"Briefing {briefing_id} not found")
    result = score_briefing_quality(briefing)
    if result["score"] < min_score:
        result["alert_id"] = await create_quality_alert(
            "briefing_quality",
            "warning",
            briefing_id,
            {"score": result["score"], "min_score": min_score, "checks": result["checks"]},
        )
    return result
