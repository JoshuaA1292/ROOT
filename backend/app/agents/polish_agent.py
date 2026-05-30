"""
Release Polish Agent: final gate before a public comment is stored.

The drafting model may return a strong but unfinished answer under quota,
latency, or token pressure. This agent makes release readiness deterministic:
it checks structure, removes truncated drafts, and emits a complete concise
filing from the verified ROOT evidence packet when the model output is not
fit to publish.
"""
from __future__ import annotations

from app.models.briefing import CoalitionSummary, DeveloperSnapshot, PolicyRef, PrecedentRef


REQUIRED_SECTIONS = (
    "### 1. Opening Statement",
    "### 2. Ecosystem Impact",
    "### 3. Developer Compliance History",
    "### 4. Relevant Precedents",
    "### 5. Policy Contradictions",
    "### 6. Requested Conditions",
    "### 7. Closing",
    "Citations & Data Sources",
)

CORE_EVIDENCE_MARKERS = (
    "permit",
    "canopy",
    "stormwater",
    "co2",
    "survival",
    "replacement",
    "condition",
    "verification",
)

TRUNCATED_ENDINGS = (
    ",", ";", ":", " and", " or", " le", " leadin", " leading", " matc",
    " match", " that", " the", " of", " with", " for", " to", " in",
)


def run(
    draft: str,
    permit: dict,
    coalition: CoalitionSummary,
    developer: DeveloperSnapshot,
    precedents: list[PrecedentRef],
    policies: list[PolicyRef] | None = None,
) -> str:
    """
    Return a complete, release-ready public comment.

    The happy path lightly normalizes a complete model draft. The safety path
    replaces incomplete output with a concise deterministic filing built from
    structured agent evidence.
    """
    policies = policies or []
    normalized = _normalize(draft)
    if _is_release_ready(normalized):
        return normalized
    return _professional_comment(permit, coalition, developer, precedents, policies)


def _normalize(draft: str) -> str:
    text = (draft or "").strip()
    if not text:
        return ""
    text = text.replace("CO\u2082", "CO2")
    text = text.replace("OneNYC 2050 Urban Forest Strategy", "the city's urban forest and climate-resilience policy record")
    text = _remove_public_section_headers(text)
    return text


def _is_release_ready(draft: str) -> bool:
    text = (draft or "").strip()
    if len(text.split()) < 220:
        return False
    # Accept both markdown headers and the cleaned uppercase versions
    has_citations = "Citations & Data Sources" in text or "CITATIONS" in text
    if not has_citations:
        return False
    lower = text.lower()
    if any(marker not in lower for marker in CORE_EVIDENCE_MARKERS):
        return False
    condition_count = lower.count("require ")
    if condition_count < 3:
        return False
    if "contact:" not in lower:
        return False
    tail = text[-100:].strip().lower()
    if tail.endswith(TRUNCATED_ENDINGS):
        return False
    if text[-1:] not in {".", "]", ")"}:
        return False
    main_text = lower.split("citations", 1)[0]
    if len(main_text.split()) < 220:
        return False
    return True


def _remove_public_section_headers(text: str) -> str:
    """Remove internal drafting headers while retaining the citations label."""
    citation_headers = {
        "### Citations & Data Sources",
        "## Citations & Data Sources",
        "Citations & Data Sources",
        "CITATIONS & DATA SOURCES",
    }
    hidden_headers = set(REQUIRED_SECTIONS[:-1])
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in citation_headers:
            lines.append("")
            lines.append("CITATIONS & DATA SOURCES")
            lines.append("")
        elif stripped in hidden_headers:
            continue
        elif stripped.startswith("### ") or stripped.startswith("## "):
            continue
        else:
            lines.append(line)
    result = "\n".join(lines)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result.strip()


def _policy_lines(policies: list[PolicyRef]) -> str:
    if not policies:
        return (
            "- Require the applicant to reconcile the removal request with the city's "
            "canopy, stormwater, carbon, and heat-resilience commitments before approval."
        )
    return "\n".join(
        f"- {p.title} ({p.section}): {p.text_excerpt}"
        for p in policies[:4]
    )


def _precedent_lines(precedents: list[PrecedentRef]) -> str:
    if not precedents:
        return (
            "No sufficiently similar precedent was found in the current ROOT corpus. "
            "That absence does not support unconditional approval. The developer ledger, "
            "the quantified ecosystem loss, and the policy conflicts below are sufficient "
            "grounds for enforceable conditions."
        )
    return "\n".join(
        f"- {p.title} ({p.year}) - outcome: {p.outcome.replace('_', ' ')}; "
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
    promised = permit.get("promised_replacements", 0)
    target_pct = developer.city_target * 100
    compliance_pct = developer.compliance_rate * 100
    bond_basis = max(5000, round(coalition.total_ecosystem_usd_yr * 1.5 / 100) * 100)
    tree_word = "tree" if coalition.tree_count == 1 else "trees"
    violation_word = "violation" if developer.violations_count == 1 else "violations"

    return f"""I am filing this public comment for agency review of Permit {permit_id} at {address}. The application seeks removal of {coalition.tree_count} street {tree_word} for a {project_type} project. Approval should be withheld unless the applicant accepts enforceable replacement, survival-verification, and reporting conditions.

ROOT calculates a loss of {coalition.canopy_sqft:,.0f} square feet of canopy, {coalition.stormwater_gal_yr:,.0f} gallons of annual stormwater interception, {coalition.co2_lbs_lifetime:,.0f} pounds of lifetime CO2 storage, ${coalition.cooling_usd_yr:,.2f} in annual cooling value, and ${coalition.total_ecosystem_usd_yr:,.2f} in total annual ecosystem value. The affected area is EJ {coalition.ej_tier}, with approximately {coalition.heat_vulnerable_residents:,} heat-vulnerable residents tied to the shade record.

{developer.name} has a replacement-survival record that warrants heightened review. Across {developer.permits_filed} prior permits, the developer promised {developer.promised_replacements} replacement trees, but only {developer.verified_surviving} are verified as surviving — a {compliance_pct:.0f}% survival rate against the city's {target_pct:.0f}% target. ROOT identifies {developer.at_risk_replacements} replacement trees below the target benchmark and {developer.violations_count} documented {violation_word}.

{_precedent_lines(precedents)}

The permit record states the removal is requested for {reason}. That record does not show how replacement survival will be verified, how canopy services will be restored, or how the applicant's past survival rate will be corrected. These policy references should be addressed before approval:
{_policy_lines(policies)}

- Require a replacement performance bond of at least ${bond_basis:,.0f}, or a higher amount set by the agency.
- Require the applicant to plant and maintain {promised} replacement trees, with species, caliper, location, watering schedule, and maintenance responsibility listed before approval.
- Require independent arborist inspection with dated photo documentation at 12 months, 36 months, and 60 months after planting.
- Require GPS-tagged planting records submitted to NYC Parks ForMS within 30 days of installation.
- Require public survival updates to attach to future permit applications by {developer.name} or related entities.
- Require the applicant to explain how the plan offsets {coalition.stormwater_gal_yr:,.0f} gallons of annual stormwater interception and {coalition.canopy_sqft:,.0f} square feet of canopy.

For these reasons, I request that the agency deny unconditional approval of Permit {permit_id}. If approval is considered, it should be conditioned on enforceable replacement, inspection, and survival-reporting obligations that remain visible in the public record. Contact: [resident name and email].

CITATIONS & DATA SOURCES

- ROOT coalition analysis for Permit {permit_id}: tree count, canopy, stormwater, CO2, cooling, and total annual ecosystem value.
- USDA i-Tree Benefits methodology for urban tree ecosystem service valuation.
- ROOT Developer Accountability Ledger for {developer.name}: prior permits, promised replacements, verified surviving replacements, compliance rate, and documented violations.
- NYC Parks tree replacement and street tree work record references, including ForMS planting verification.
- City canopy, stormwater, and heat-resilience policy references stored in the ROOT city policy corpus.
"""
