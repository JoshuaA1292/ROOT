"""
Demo simulation endpoint.

Allows a single-click "fast-forward" to any guardian milestone so a demo
can show the full agentic lifecycle in under 3 minutes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.db.repositories.briefings import get_briefing_by_id, update_briefing
from app.db.repositories.permits import get_permit_by_id
from app.services.notification_service import notify_guardian_check

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/start")
async def demo_start(body: dict):
    """
    Auto-demo entrypoint.
    1. Finds the first permit with threatened trees.
    2. Clears any existing briefings for that permit.
    3. Starts the analysis pipeline.
    4. Returns briefing_id and permit info so the frontend can stream progress.
    The frontend then auto-submits with the provided email when done.
    """
    from app.db.client import get_db
    from app.db.repositories.permits import get_permit_by_id
    from app.agents.orchestrator import start_pipeline

    email: str = body.get("email", "").strip()
    if not email:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="email required")

    db = get_db()

    # Find first permit with threatened trees
    permit_doc = await db.permits.find_one({"threatened_tree_ids.0": {"$exists": True}})
    if not permit_doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No permits with threatened trees found")

    permit_id = str(permit_doc["_id"])

    # Clear existing briefings for this permit so demo is fresh
    await db.briefings.delete_many({"permit_id": permit_id})

    briefing_id = await start_pipeline(permit_id)

    return {
        "briefing_id": briefing_id,
        "permit_id": permit_id,
        "address": permit_doc.get("address", ""),
        "email": email,
    }

_STEP_LABELS = {
    "day90": "Day 90 Permit Status Check",
    "month12": "Month 12 Planting Promise Audit",
    "month36": "Month 36 Survival Verification",
    "year5": "Year 5 Case Closure",
}

_NEXT_STEPS = {
    "day90": "month12",
    "month12": "month36",
    "month36": "year5",
    "year5": None,
}


async def _generate_guardian_report(
    step: str,
    address: str,
    developer_name: str,
    compliance_rate: float,
    tree_count: int,
    ecosystem_usd_yr: float,
    draft_comment: str,
) -> str:
    """Generate guardian check report via LLM, falling back to a deterministic template."""
    from app.config import settings

    label = _STEP_LABELS.get(step, step)
    pct = round(compliance_rate * 100)
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Try Gemini
    if settings.gemini_api_key or settings.google_cloud_project:
        try:
            import google.generativeai as genai
            if settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model or "gemini-2.0-flash")
            label = _STEP_LABELS.get(step, step)
            prompt = f"""Guardian audit — {label} for {address}.
Developer {developer_name}: {pct}% survival vs 85% target. {tree_count} trees at risk.
Write a 3-paragraph audit report for {now}: what was checked, what was found (be realistic based on {pct}% compliance), next action. Concise and data-driven."""
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except Exception:
            pass

    # Deterministic fallback
    return _deterministic_report(step, address, developer_name, pct, tree_count, ecosystem_usd_yr, now)


def _deterministic_report(
    step: str,
    address: str,
    developer_name: str,
    pct: int,
    tree_count: int,
    ecosystem_usd_yr: float,
    now: str,
) -> str:
    if step == "day90":
        status = "ACTIVE — no construction start recorded" if pct < 70 else "APPROVED WITH CONDITIONS"
        return f"""Day 90 audit completed on {now}.

Permit status at {address}: {status}. The removal permit filed by {developer_name} has not been resolved. ROOT cross-referenced the NYC DOB permit database and confirmed no demolition permits or tree work start notices have been filed.

Developer compliance history remains at {pct}% verified replacement survival, {85 - pct} points below the city's 85% benchmark. The intervention comment filed at Day 1 is on record. {tree_count} trees remain in the impact zone with ${ecosystem_usd_yr:,.0f}/year in threatened ecosystem services.

Next action: Month 12 planting promise audit will verify whether replacement trees were installed and GPS-tagged in NYC Parks ForMS. {developer_name}'s ledger will update automatically."""

    elif step == "month12":
        planted = max(0, round(tree_count * (pct / 100) * 0.8))
        missing = tree_count - planted
        return f"""Month 12 planting audit completed on {now}.

ROOT queried NYC Parks ForMS planting records for {address}. {planted} of {tree_count} promised replacement trees have GPS-tagged planting records. {missing} trees are unaccounted for — no ForMS entry, no inspection record, no species documentation.

{developer_name}'s compliance record has been updated to reflect {planted}/{tree_count} planted. Missing plantings have been escalated to the enforcement queue. A formal notice of non-compliance has been added to the permit record.

Next action: Month 36 survival verification will cross-reference inspection records to determine which planted trees are alive. ROOT will notify you when the audit runs."""

    elif step == "month36":
        surviving = max(0, round(tree_count * (pct / 100) * 0.7))
        return f"""Month 36 survival check completed on {now}.

ROOT cross-referenced NYC Parks inspection records against the planting manifest for {address}. {surviving} of {tree_count} replacement trees have been confirmed alive via inspection records. The rest have no inspection entry or are documented as dead/removed.

Developer ledger updated: {developer_name} now has a verified 36-month survival rate of {round(surviving / tree_count * 100)}% for this permit. This record will be attached to all future permit applications by this developer and their linked entities.

Next action: Year 5 final case closure will compute the ecosystem service debt and close the guardian record. The developer's permanent permit history will be updated."""

    else:  # year5
        return f"""Year 5 case closure completed on {now}.

ROOT has completed the full guardian lifecycle for {address}. Final compliance record: {developer_name} delivered {pct}% of promised replacement trees with verified survival. The city target is 85%.

Ecosystem service debt computed: ${max(0, (85 - pct) / 100 * tree_count * 1800):,.0f} in undelivered annual ecosystem services over the 5-year period. This figure has been attached to {developer_name}'s permanent permit history and will influence future permit review scores.

Case status: CLOSED. The guardian record is now part of ROOT's public accountability database. {developer_name}'s risk tier has been updated for future permit applicants."""


@router.post("/simulate-guardian")
async def simulate_guardian_check(body: dict):
    """
    Fast-forward to a guardian milestone for demo purposes.
    Runs the guardian check agent, generates an audit report, creates a notification.
    """
    briefing_id = body.get("briefing_id")
    step = body.get("step", "day90")

    if not briefing_id:
        raise HTTPException(status_code=400, detail="briefing_id required")
    if step not in _STEP_LABELS:
        raise HTTPException(status_code=400, detail=f"step must be one of {list(_STEP_LABELS.keys())}")

    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")

    permit_id = briefing.get("permit_id", "")
    permit = await get_permit_by_id(permit_id) if permit_id else None
    address = permit.get("address", "Unknown address") if permit else "Unknown address"

    dev_snapshot = briefing.get("developer_snapshot") or {}
    developer_name = dev_snapshot.get("name", "Unknown Developer")
    compliance_rate = float(dev_snapshot.get("compliance_rate", 0.5))

    coalition = briefing.get("coalition_summary") or {}
    tree_count = int(coalition.get("tree_count", 1))
    ecosystem_usd_yr = float(coalition.get("total_ecosystem_usd_yr", 0))

    draft_comment = briefing.get("draft_comment", "")

    audit_report = await _generate_guardian_report(
        step, address, developer_name, compliance_rate,
        tree_count, ecosystem_usd_yr, draft_comment,
    )

    gs: dict = briefing.get("guardian_schedule") or {}
    next_step = _NEXT_STEPS.get(step)
    next_check_date = gs.get(next_step) if next_step else None

    notification_id = await notify_guardian_check(
        briefing_id=briefing_id,
        permit_id=permit_id,
        address=address,
        step=step,
        audit_report=audit_report,
        next_check=next_step,
        next_check_date=next_check_date,
    )

    # Mark the simulated step as completed in the guardian schedule
    now_iso = datetime.now(timezone.utc).isoformat()
    await update_briefing(briefing_id, {
        f"guardian_schedule.{step}_status": "completed",
        f"guardian_schedule.{step}_completed_at": now_iso,
        "guardian_schedule.next_check": next_step or "complete",
    })

    return {
        "status": "ok",
        "step": step,
        "step_label": _STEP_LABELS[step],
        "address": address,
        "audit_report": audit_report,
        "notification_id": notification_id,
        "next_step": next_step,
        "next_check_date": next_check_date,
    }
