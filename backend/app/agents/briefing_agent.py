"""
Briefing Agent: synthesises all agent outputs into a legally-grounded public
comment draft.

Primary: Gemini via google.genai (AI Studio key or Vertex AI).

Auth:
  Gemini  — GOOGLE_AI_STUDIO_KEY  or  GOOGLE_CLOUD_PROJECT
"""
from __future__ import annotations

import os
from pathlib import Path

from app.agents import polish_agent
from app.config import settings
from app.models.briefing import CoalitionSummary, DeveloperSnapshot, PolicyRef, PrecedentRef

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "briefing_system.md").read_text()

# ── Gemini client (lazy) ───────────────────────────────────────────────────

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai as genai_client

        api_key = (
            settings.google_ai_studio_key
            or settings.gemini_api_key
            or os.environ.get("GOOGLE_AI_STUDIO_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if api_key:
            _gemini_client = genai_client.Client(api_key=api_key)
        elif settings.google_cloud_project:
            _gemini_client = genai_client.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )
        else:
            raise RuntimeError(
                "No Gemini credentials. Set GOOGLE_AI_STUDIO_KEY or GOOGLE_CLOUD_PROJECT."
            )
    return _gemini_client


# ── Retryable error detection ─────────────────────────────────────────────

_EXHAUSTION_PHRASES = (
    "429", "quota", "resource_exhausted", "resourceexhausted",
    "rate limit", "503", "unavailable", "high demand",
)


def _is_gemini_exhausted(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(p in msg for p in _EXHAUSTION_PHRASES)


# ── Prompt builder ────────────────────────────────────────────────────────

def _build_user_prompt(
    permit: dict,
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    precedents: list[PrecedentRef],
    policies: list[PolicyRef],
) -> str:
    precedent_text = "\n".join(
        f"- [{p.year}] {p.title} — outcome: {p.outcome}, "
        f"arguments: {', '.join(p.arguments_used)}, "
        f"match: {p.similarity_score:.0%}"
        for p in precedents
    )
    policy_text = "\n".join(
        f"- {p.title} ({p.section}) — {p.text_excerpt}"
        for p in policies
    )

    return (
        f"## Permit\n"
        f"Address: {permit.get('address')}\n"
        f"Project type: {permit.get('project_type', '').replace('_', ' ')}\n"
        f"Stated reason: {permit.get('stated_reason')}\n"
        f"Promised replacements: {permit.get('promised_replacements')}\n"
        f"Comment deadline: {permit.get('comment_deadline')}\n\n"
        f"## Coalition Impact\n"
        f"Trees threatened: {coalition.tree_count}\n"
        f"Combined canopy: {coalition.canopy_sqft:,.0f} sq ft\n"
        f"Annual stormwater: {coalition.stormwater_gal_yr:,.0f} gallons\n"
        f"Lifetime CO₂: {coalition.co2_lbs_lifetime:,.0f} lbs\n"
        f"Annual cooling value: ${coalition.cooling_usd_yr:,.2f}\n"
        f"Total annual ecosystem value: ${coalition.total_ecosystem_usd_yr:,.2f}\n"
        f"EJ tier: {coalition.ej_tier}\n"
        f"Residents losing shade: ~{coalition.heat_vulnerable_residents}\n\n"
        f"## Developer Compliance Record\n"
        f"Name: {developer.name}\n"
        f"Prior permits: {developer.permits_filed}\n"
        f"Promised replacements: {developer.promised_replacements}\n"
        f"Verified surviving: {developer.verified_surviving}\n"
        f"Compliance rate: {developer.compliance_rate * 100:.0f}%\n"
        f"City target: {developer.city_target * 100:.0f}%\n"
        f"Target delta: {developer.target_delta * 100:.0f} percentage points\n"
        f"Replacement trees below target: {developer.at_risk_replacements}\n"
        f"Documented violations: {developer.violations_count}\n\n"
        f"## Relevant Precedents\n"
        f"{precedent_text or 'None found.'}\n\n"
        f"## City Policy References\n"
        f"{policy_text or 'None found.'}\n\n"
        "---\nDraft the complete public comment package now. Keep it concise: 500-750 words total. Finish all seven sections and the citations appendix."
    )


def _extract_citations(draft: str) -> list[str]:
    if "Citations & Data Sources" not in draft:
        return []
    block = draft.split("Citations & Data Sources")[1].strip().lstrip("#").strip()
    return [
        ln.strip().lstrip("-").strip()
        for ln in block.split("\n")
        if ln.strip().startswith("-")
    ]


_REQUIRED_SECTIONS = (
    "### 1. Opening Statement",
    "### 2. Ecosystem Impact",
    "### 3. Developer Compliance History",
    "### 4. Relevant Precedents",
    "### 5. Policy Contradictions",
    "### 6. Requested Conditions",
    "### 7. Closing",
    "Citations & Data Sources",
)


def _is_incomplete_draft(draft: str) -> bool:
    text = (draft or "").strip()
    if len(text.split()) < 220:
        return True
    if any(section not in text for section in _REQUIRED_SECTIONS):
        return True
    tail = text[-100:].strip().lower()
    if tail.endswith((",", ";", ":", " and", " or", " le", " leadin", " leading", " matc", " match", " that", " the")):
        return True
    if text[-1:] not in {".", "]", ")"}:
        return True
    return False


def _policy_lines(policies: list[PolicyRef]) -> str:
    if not policies:
        return (
            "- Require the applicant to reconcile the removal request with the city's "
            "published canopy, stormwater, and heat-resilience commitments before approval."
        )
    return "\n".join(
        f"- {p.title} ({p.section}): {p.text_excerpt}"
        for p in policies
    )


def _precedent_lines(precedents: list[PrecedentRef]) -> str:
    if not precedents:
        return (
            "No sufficiently similar precedent was found in the current ROOT corpus. "
            "That absence should not be read as support for unconditional approval. "
            "The developer's documented replacement-survival record, the high heat-vulnerability "
            "context, and the policy conflicts below provide an independent basis for enforceable conditions."
        )
    return "\n".join(
        f"- {p.title} ({p.year}) — outcome: {p.outcome.replace('_', ' ')}; "
        f"arguments used: {', '.join(p.arguments_used) or 'not specified'}; "
        f"semantic match: {p.similarity_score:.0%}."
        for p in precedents[:3]
    )


def _professional_comment(
    permit: dict,
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    precedents: list[PrecedentRef],
    policies: list[PolicyRef],
) -> str:
    address = permit.get("address", "the subject property")
    permit_id = permit.get("_id") or permit.get("id") or "the pending permit"
    project_type = str(permit.get("project_type", "tree work")).replace("_", " ")
    reason = permit.get("stated_reason") or "the stated project scope"
    promised = permit.get("promised_replacements", "the proposed")
    target_pct = developer.city_target * 100
    compliance_pct = developer.compliance_rate * 100
    delta_pts = developer.target_delta * 100
    requested_bond_basis = max(5000, round(coalition.total_ecosystem_usd_yr * 1.5 / 100) * 100)

    return f"""### 1. Opening Statement
I am filing this public comment for agency review of Permit {permit_id} at {address}, which seeks removal of {coalition.tree_count} street tree{'s' if coalition.tree_count != 1 else ''} for a {project_type} project. The application should not receive unconditional approval without enforceable replacement, verification, and survival conditions.

### 2. Ecosystem Impact
ROOT calculates {coalition.canopy_sqft:,.0f} square feet of canopy, {coalition.stormwater_gal_yr:,.0f} gallons of annual stormwater interception, {coalition.co2_lbs_lifetime:,.0f} pounds of lifetime CO2 storage, ${coalition.cooling_usd_yr:,.2f} in annual cooling value, and ${coalition.total_ecosystem_usd_yr:,.2f} in total annual ecosystem value. The affected location is classified as EJ {coalition.ej_tier}, with approximately {coalition.heat_vulnerable_residents:,} heat-vulnerable residents tied to the shade record. The applicant should explain on the record how these quantified services will be replaced and verified.

### 3. Developer Compliance History
{developer.name} has a documented replacement-survival record that warrants heightened review. Across {developer.permits_filed} prior permit{'s' if developer.permits_filed != 1 else ''}, the developer promised {developer.promised_replacements} replacement trees, but only {developer.verified_surviving} are verified as surviving: a {compliance_pct:.0f}% survival rate versus the city's {target_pct:.0f}% target. ROOT also identifies {developer.at_risk_replacements} replacement tree{'s' if developer.at_risk_replacements != 1 else ''} below the target benchmark and {developer.violations_count} documented violation{'s' if developer.violations_count != 1 else ''}; this record makes independent verification necessary.

### 4. Relevant Precedents
{_precedent_lines(precedents)}

### 5. Policy Contradictions
The application should be reconciled with the city's published canopy, stormwater, carbon, and heat-resilience commitments before approval. The permit record states the removal is requested for {reason}, but the current record does not show how replacement survival will be verified. The following policy references should be addressed on the record:
{_policy_lines(policies)}

### 6. Requested Conditions
- Require a replacement performance bond of at least ${requested_bond_basis:,.0f}, or a higher amount set by the agency.
- Require independent arborist inspection with photo documentation at 12 months, 36 months, and 60 months after planting.
- Require GPS-tagged replacement planting records submitted to NYC Parks ForMS within 30 days of installation.
- Require species, caliper, planting location, maintenance responsibility, and watering schedule for each replacement tree before approval.
- Require public survival updates to be attached to future permit applications by {developer.name} or related entities.
- Require the applicant to answer on the record how the plan offsets {coalition.stormwater_gal_yr:,.0f} gallons of annual stormwater interception and {coalition.canopy_sqft:,.0f} square feet of canopy.

### 7. Closing
For these reasons, I request that the agency withhold unconditional approval of Permit {permit_id} unless the applicant accepts enforceable replacement, inspection, and survival-reporting conditions on the record. Please include this comment in the permit record and provide a written response addressing developer compliance history, heat vulnerability, and replacement verification. Contact: [resident name and email].

### Citations & Data Sources
- ROOT coalition analysis for Permit {permit_id}: tree count, canopy, stormwater, CO2, cooling, and total annual ecosystem value.
- USDA i-Tree Benefits methodology for urban tree ecosystem service valuation.
- ROOT Developer Accountability Ledger for {developer.name}: prior permits, promised replacements, verified surviving replacements, compliance rate, and documented violations.
- NYC Parks tree replacement and street tree work record references, including ForMS planting verification.
- City canopy, stormwater, and heat-resilience policy references stored in the ROOT city policy corpus.
"""


def _finalize_draft(
    draft: str,
    permit: dict,
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    precedents: list[PrecedentRef],
    policies: list[PolicyRef],
) -> str:
    if _is_incomplete_draft(draft):
        return _professional_comment(permit, coalition, developer, precedents, policies)
    return draft.strip()


# ── Primary: Gemini ───────────────────────────────────────────────────────

async def _run_gemini(user_prompt: str) -> str:
    from google.genai import types as genai_types

    client = _get_gemini_client()
    model = settings.gemini_model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    response = await client.aio.models.generate_content(
        model=model,
        contents=[
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_prompt)],
            )
        ],
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=1800,
        ),
    )
    return response.text or ""


# ── Public entry point ────────────────────────────────────────────────────

async def run(
    permit: dict,
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    precedents: list[PrecedentRef],
    policies: list[PolicyRef] | None = None,
) -> tuple[str, list[str]]:
    """
    Returns (draft_comment_markdown, citations_list).

    Raises RuntimeError with a user-friendly message on Gemini quota exhaustion.
    """
    user_prompt = _build_user_prompt(
        permit, coalition, developer, precedents, policies or []
    )

    try:
        draft = await _run_gemini(user_prompt)
        draft = polish_agent.run(draft, permit, coalition, developer, precedents, policies or [])
        return draft, _extract_citations(draft)

    except Exception as gemini_exc:
        if not _is_gemini_exhausted(gemini_exc):
            raise
        raise RuntimeError(
            "The Gemini API has been called too many times. Please try again later."
        ) from gemini_exc
