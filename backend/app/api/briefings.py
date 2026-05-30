from datetime import datetime, timedelta, timezone
from urllib.parse import quote, quote_plus
import re
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException

_log = logging.getLogger(__name__)
from app.db.repositories.briefings import (
    get_briefing_by_id,
    update_briefing,
    get_latest_briefing_for_permit,
)
from app.db.repositories.briefing_jobs import get_briefing_job
from app.db.repositories.permits import get_permit_by_id
from app.models.briefing import BriefingPatch
from app.agents.orchestrator import start_pipeline
from app.services.quality import evaluate_briefing_quality, score_briefing_quality

router = APIRouter(prefix="/briefings", tags=["briefings"])


async def _ensure_case_file_fields(briefing: dict) -> dict:
    """Backfill strategy/evidence fields for older briefing records."""
    if briefing.get("intervention_strategy") and briefing.get("evidence_board"):
        return briefing

    coalition = briefing.get("coalition_summary") or {}
    developer = briefing.get("developer_snapshot") or {}
    if not coalition or not developer:
        return briefing

    from app.services.strategy import build_evidence_board, build_intervention_strategy

    precedents = briefing.get("precedent_refs") or []
    policies = briefing.get("policy_refs") or []
    update_data = {
        "intervention_strategy": build_intervention_strategy(coalition, developer, precedents, policies),
        "evidence_board": build_evidence_board(coalition, developer, precedents, policies),
    }
    await update_briefing(str(briefing["_id"]), update_data)
    briefing.update(update_data)
    return briefing


@router.get("/defense-map")
async def defense_map():
    """Return tree IDs with submitted defense counts for map overlay."""
    from app.db.client import get_db
    db = get_db()
    cursor = db.briefings.find(
        {"status": "submitted"},
        {"permit_id": 1, "guardian_emails": 1, "submitted_by_email": 1},
    )
    permit_counts: dict[str, int] = {}
    async for doc in cursor:
        permit_id = doc.get("permit_id", "")
        if not permit_id:
            continue
        emails = {
            str(email).strip().lower()
            for email in (doc.get("guardian_emails") or [])
            if str(email).strip()
        }
        submitted_by = str(doc.get("submitted_by_email") or "").strip().lower()
        if submitted_by:
            emails.add(submitted_by)
        permit_counts[permit_id] = permit_counts.get(permit_id, 0) + max(1, len(emails))

    if not permit_counts:
        return {"defenses": []}

    defenses: dict[str, int] = {}
    for pid, count in permit_counts.items():
        permit = await get_permit_by_id(pid)
        if not permit:
            continue
        for tid in permit.get("threatened_tree_ids", []):
            defenses[tid] = defenses.get(tid, 0) + count

    return {"defenses": [{"tree_id": tid, "count": cnt} for tid, cnt in defenses.items()]}


@router.post("")
async def trigger_briefing(body: dict):
    """
    Trigger the full agent pipeline for a permit.
    If a submitted briefing already exists for this permit, return it directly
    (status="already_submitted") so the frontend can show the existing guardian
    case instead of re-running the pipeline.
    """
    permit_id = body.get("permit_id")
    if not permit_id:
        raise HTTPException(status_code=400, detail="permit_id required")

    existing = await get_latest_briefing_for_permit(permit_id)
    if existing and existing.get("status") == "submitted":
        existing = await _ensure_case_file_fields(existing)
        if not existing.get("coalition_summary") or not existing.get("developer_snapshot"):
            briefing_id = await start_pipeline(permit_id)
            return {"briefing_id": briefing_id, "status": "running"}
        existing["id"] = str(existing.pop("_id"))
        return {"briefing_id": existing["id"], "status": "already_submitted", "briefing": existing}

    briefing_id = await start_pipeline(permit_id)
    return {"briefing_id": briefing_id, "status": "running"}


@router.get("/{briefing_id}")
async def get_briefing(briefing_id: str):
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    briefing = await _ensure_case_file_fields(briefing)
    briefing["id"] = str(briefing.pop("_id"))
    return briefing


@router.get("/{briefing_id}/job")
async def get_briefing_job_status(briefing_id: str):
    job = await get_briefing_job(briefing_id)
    if not job:
        raise HTTPException(status_code=404, detail="Briefing job not found")
    job["id"] = str(job.pop("_id"))
    return job


@router.get("/{briefing_id}/quality")
async def get_briefing_quality(briefing_id: str):
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return score_briefing_quality(briefing)


@router.post("/{briefing_id}/quality/evaluate")
async def evaluate_quality(briefing_id: str, min_score: int = 75):
    try:
        return await evaluate_briefing_quality(briefing_id, min_score)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{briefing_id}")
async def patch_briefing(briefing_id: str, body: BriefingPatch):
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")

    update_data: dict = {}

    if body.draft_comment is not None:
        update_data["edits"] = briefing.get("edits", []) + [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_text": briefing.get("draft_comment", ""),
            "new_text": body.draft_comment,
        }]
        update_data["draft_comment"] = body.draft_comment
        if body.status is None and briefing.get("status") != "submitted":
            update_data["status"] = "edited"

    if body.status is not None:
        update_data["status"] = body.status

    if body.reviewed_by_email is not None:
        update_data["reviewed_by_email"] = body.reviewed_by_email

    if update_data:
        await update_briefing(briefing_id, update_data)

    updated = await get_briefing_by_id(briefing_id)
    updated["id"] = str(updated.pop("_id"))
    return updated


_BORO_CODES = {
    "manhattan": "1", "bronx": "2", "brooklyn": "3", "queens": "4", "staten island": "5",
}

# ZIP prefix → borough (fallback when borough name isn't in the address string)
_ZIP_PREFIX_BORO = {
    "100": "manhattan", "101": "manhattan", "102": "manhattan",
    "104": "bronx",
    "103": "staten island",
    "112": "brooklyn", "111": "brooklyn", "113": "brooklyn",
    "116": "queens", "114": "queens", "115": "queens",
}


def _extract_borough(address: str) -> str:
    """Extract borough from an NYC address string like '487 Atlantic Ave, Brooklyn, NY 11217'."""
    addr_lower = (address or "").lower()
    # Direct name match (handles "Staten Island" before "Island" substring)
    for name in ("staten island", "manhattan", "bronx", "brooklyn", "queens"):
        if name in addr_lower:
            return name
    # ZIP-code fallback
    zip_match = re.search(r"\b(1\d{4})\b", address)
    if zip_match:
        return _ZIP_PREFIX_BORO.get(zip_match.group(1)[:3], "brooklyn")
    return "brooklyn"


def _parse_address(address: str) -> tuple[str, str]:
    """Return (house_number, street_name) from a NYC address string."""
    m = re.match(r"^(\d+[A-Za-z]?)\s+(.+?)(?:,|$)", (address or "").strip())
    if m:
        return m.group(1), m.group(2).upper().strip()
    return "", (address or "").upper()


def _build_nyc_dob_url(address: str) -> str:
    """
    BIS Property Profile — shows all jobs, permits, and violations at the
    address.  More reliable than PermitsByAddress for advocates because it
    doesn't require an exact permit number.
    """
    borough = _extract_borough(address)
    boro_code = _BORO_CODES.get(borough, "3")
    house, street = _parse_address(address)
    street_enc = quote_plus(street)
    return (
        f"https://a810-bisweb.nyc.gov/bisweb/PropertyProfileOverviewServlet"
        f"?requestid=1&boro={boro_code}&houseno={house}&street={street_enc}"
    )


def _build_maps_url(address: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"


def _build_parks_email_url(address: str, draft_comment: str) -> str:
    """
    Pre-filled mailto to NYC Parks Urban Forestry — the agency that actually
    administers tree removal permits and accepts public comments.
    Body is truncated to stay within safe mailto length limits (~1,800 chars).
    """
    subject = f"Public Comment — Tree Removal Permit: {address}"
    body = (draft_comment or "")[:1800]
    return (
        f"mailto:UrbanForestry@parks.nyc.gov"
        f"?subject={quote(subject, safe='')}"
        f"&body={quote(body, safe='')}"
    )


@router.post("/{briefing_id}/submit")
async def submit_briefing(briefing_id: str, background: BackgroundTasks, body: dict = {}):
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")

    submitted_email: str = body.get("email", "").strip() if body else ""

    already_submitted = briefing.get("status") == "submitted"

    if already_submitted:
        # Reuse the original guardian schedule so all defenders share the same timeline
        guardian_schedule = briefing.get("guardian_schedule") or {}
        # Backfill if somehow missing
        if not guardian_schedule:
            submitted_at = datetime.now(timezone.utc)
            guardian_schedule = {
                "day90":   (submitted_at + timedelta(days=90)).isoformat(),
                "month12": (submitted_at + timedelta(days=365)).isoformat(),
                "month36": (submitted_at + timedelta(days=1095)).isoformat(),
                "year5":   (submitted_at + timedelta(days=1825)).isoformat(),
                "next_check": "day90",
            }
        # Add this defender's email to the list (no duplicates)
        if submitted_email:
            from app.db.client import get_db
            db = get_db()
            await db.briefings.update_one(
                {"_id": briefing["_id"]},
                {"$addToSet": {"guardian_emails": submitted_email}},
            )
            briefing = await get_briefing_by_id(briefing_id) or briefing
    else:
        submitted_at = datetime.now(timezone.utc)
        guardian_schedule = {
            "day90":   (submitted_at + timedelta(days=90)).isoformat(),
            "month12": (submitted_at + timedelta(days=365)).isoformat(),
            "month36": (submitted_at + timedelta(days=1095)).isoformat(),
            "year5":   (submitted_at + timedelta(days=1825)).isoformat(),
            "next_check": "day90",
        }
        update_fields: dict = {
            "status": "submitted",
            "submitted_at": submitted_at.isoformat(),
            "guardian_schedule": guardian_schedule,
        }
        if submitted_email:
            update_fields["submitted_by_email"] = submitted_email
            update_fields["guardian_emails"] = [submitted_email]
        await update_briefing(briefing_id, update_fields)
        briefing = await get_briefing_by_id(briefing_id) or briefing

    permit = await get_permit_by_id(briefing.get("permit_id", ""))
    address = permit.get("address", "") if permit else ""
    draft   = briefing.get("draft_comment", "")

    # Create the in-app notification before responding so the UI inbox can
    # update immediately. The slower external email send happens in the
    # background and logs failures without hiding the submitted state.
    from app.services.notification_service import (
        build_guardian_activated_message,
        notify_guardian_activated,
        _send_email,
    )

    dev_snapshot = briefing.get("developer_snapshot") or {}
    coalition    = briefing.get("coalition_summary") or {}

    compliance_rate = float(dev_snapshot.get("compliance_rate", 0.5))
    if compliance_rate >= 0.85:
        risk_tier = "compliant"
    elif compliance_rate >= 0.60:
        risk_tier = "elevated"
    elif compliance_rate >= 0.40:
        risk_tier = "high"
    else:
        risk_tier = "critical"

    notification_id = await notify_guardian_activated(
        briefing_id=briefing_id,
        permit_id=briefing.get("permit_id", ""),
        address=address,
        developer_name=dev_snapshot.get("name", "Unknown Developer"),
        compliance_rate=compliance_rate,
        risk_tier=risk_tier,
        tree_count=int(coalition.get("tree_count", 1)),
        ecosystem_usd_yr=float(coalition.get("total_ecosystem_usd_yr", 0)),
        guardian_schedule=guardian_schedule,
        recipient_email=submitted_email or None,
        send_email=False,
    )

    async def _send_guardian_email() -> None:
        if not submitted_email:
            return
        try:
            subject, body_text, body_html = build_guardian_activated_message(
                address=address,
                developer_name=dev_snapshot.get("name", "Unknown Developer"),
                compliance_rate=compliance_rate,
                risk_tier=risk_tier,
                tree_count=int(coalition.get("tree_count", 1)),
                ecosystem_usd_yr=float(coalition.get("total_ecosystem_usd_yr", 0)),
                guardian_schedule=guardian_schedule,
            )
            await _send_email(subject, body_text, body_html, submitted_email)
        except Exception as exc:
            _log.error("Guardian notification failed: %s", exc, exc_info=True)

    background.add_task(_send_guardian_email)

    defender_emails = {
        str(email).strip().lower()
        for email in (briefing.get("guardian_emails") or [])
        if str(email).strip()
    }
    submitted_by_email = str(briefing.get("submitted_by_email") or "").strip().lower()
    if submitted_by_email:
        defender_emails.add(submitted_by_email)
    defense_count = max(1, len(defender_emails)) if briefing.get("status") == "submitted" else 1

    return {
        "status": "submitted",
        "briefing_id": briefing_id,
        "defense_count": defense_count,
        "notification_id": notification_id,
        "guardian_schedule": guardian_schedule,
        "permit_address": address,
        # Three links that actually open and do something useful:
        "nyc_dob_url":      _build_nyc_dob_url(address),
        "nyc_parks_email":  _build_parks_email_url(address, draft),
        "maps_url":         _build_maps_url(address),
    }

