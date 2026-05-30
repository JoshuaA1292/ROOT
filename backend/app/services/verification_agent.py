"""
Outcome verification agent.

When a user records an outcome (e.g., "agency acknowledged comment", "surety bond
imposed"), this agent checks whether the claim is plausible given what ROOT knows
about the permit, developer, and NYC permit process.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_CONDITION_LABELS = {
    "surety_bond": "surety bond required",
    "independent_audit": "independent arborist audit mandated",
    "species_diversity": "species diversity mandate added",
    "gps_tracking": "GPS-tagged planting records required",
    "phased_review": "phased review at 1, 3, and 5 years imposed",
}


async def verify_outcome(
    permit_id: str,
    briefing_id: str | None,
    comment_acknowledged: bool,
    conditions_imposed: list[str],
    notes: str,
    developer_name: str,
    compliance_rate: float,
    tree_count: int,
    address: str,
) -> dict:
    """
    Returns {verified: bool, confidence: "high"|"medium"|"low", flags: list[str], summary: str}
    """
    from app.config import settings

    pct = round(compliance_rate * 100)
    condition_text = ", ".join(_CONDITION_LABELS.get(c, c) for c in conditions_imposed) or "none"

    prompt = f"""You are a civic data integrity agent verifying a reported permit outcome.

PERMIT: {permit_id} at {address}
DEVELOPER: {developer_name} — {pct}% replacement survival rate (city target: 85%)
TREES AT RISK: {tree_count}
CLAIMED OUTCOME:
- Agency acknowledged comment: {comment_acknowledged}
- Conditions imposed: {condition_text}
- Notes: {notes or '(none)'}

Assess whether this reported outcome is plausible given:
1. NYC DOB/Parks typically impose conditions when developer compliance is below 85%
2. Surety bonds are rare but have precedent for repeat violators
3. "Acknowledged" comments are more common than conditions in NYC

Respond ONLY with this JSON (no markdown, no explanation):
{{"verified": true/false, "confidence": "high"/"medium"/"low", "flags": ["issue1", "issue2"], "summary": "one sentence assessment"}}"""

    result = None

    if settings.gemini_api_key or settings.google_cloud_project:
        try:
            import google.generativeai as genai
            import json as _json
            if settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model or "gemini-2.0-flash")
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            result = _json.loads(raw)
        except Exception as exc:
            logger.warning("Gemini verification failed: %s", exc)

    if result is None:
        # Deterministic fallback
        result = _deterministic_verify(comment_acknowledged, conditions_imposed, pct, notes)

    return result


def _deterministic_verify(
    acknowledged: bool,
    conditions: list[str],
    pct: int,
    notes: str,
) -> dict:
    flags: list[str] = []
    verified = True

    # Surety bond is very rare from a public comment alone
    if "surety_bond" in conditions and pct > 70:
        flags.append("Surety bonds are rarely imposed when compliance rate exceeds 70%")
        verified = False

    # Claiming acknowledgment AND major conditions is unusual for first-time filers
    if acknowledged and len(conditions) >= 3 and pct > 60:
        flags.append("Full acknowledgment with 3+ conditions is uncommon for first-time comments unless developer has repeat violations")

    # No notes on a complex outcome is a weak signal
    if (acknowledged or conditions) and not notes:
        flags.append("No explanatory notes provided — add context to strengthen record")

    confidence = "high" if not flags else ("medium" if len(flags) == 1 else "low")
    summary = (
        "Outcome is consistent with known permit and developer history."
        if verified
        else "One or more claims appear inconsistent with typical NYC permit outcomes — review before saving."
    )

    return {"verified": verified, "confidence": confidence, "flags": flags, "summary": summary}
