"""
Guardian checkpoint scheduler.

Runs every hour and fires guardian-check emails for any briefings whose
next scheduled milestone (day90 / month12 / month36 / year5) has passed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_STEPS = ["day90", "month12", "month36", "year5"]
_NEXT: dict[str, str | None] = {
    "day90":   "month12",
    "month12": "month36",
    "month36": "year5",
    "year5":   None,
}
_LABELS = {
    "day90":   "Day 90 Check",
    "month12": "Month 12 Audit",
    "month36": "Month 36 Survival Check",
    "year5":   "Year 5 Case Closure",
}


async def run_guardian_checks() -> None:
    """Query DB for overdue guardian checks and send emails."""
    try:
        from app.db.client import get_db
        db = get_db()

        now_iso = datetime.now(timezone.utc).isoformat()

        # Find all submitted briefings that still have a pending next_check
        cursor = db.briefings.find(
            {
                "status": "submitted",
                "guardian_schedule.next_check": {"$in": _STEPS},
            },
            {
                "_id": 1,
                "permit_id": 1,
                "guardian_schedule": 1,
                "submitted_by_email": 1,
                "guardian_emails": 1,
            },
        )

        async for doc in cursor:
            await _process_briefing(db, doc, now_iso)

    except Exception:
        logger.exception("Guardian scheduler error during run_guardian_checks")


async def _process_briefing(db, doc: dict, now_iso: str) -> None:
    briefing_id = str(doc["_id"])
    schedule: dict = doc.get("guardian_schedule") or {}
    step: str | None = schedule.get("next_check")

    if not step or step not in _STEPS:
        return

    due_iso: str = schedule.get(step, "")
    if not due_iso:
        return

    # Normalize — remove fractional seconds for comparison
    due_dt = datetime.fromisoformat(due_iso.replace("Z", "+00:00"))
    if due_dt > datetime.now(timezone.utc):
        return  # not yet due

    permit_id = doc.get("permit_id", "")

    # Resolve address from permit
    try:
        from app.db.repositories.permits import get_permit_by_id
        permit = await get_permit_by_id(permit_id)
        address = permit.get("address", permit_id) if permit else permit_id
    except Exception:
        address = permit_id

    next_step = _NEXT.get(step)
    next_date = schedule.get(next_step, "") if next_step else None

    audit_report = (
        f"ROOT Guardian checkpoint reached: {_LABELS[step]}.\n\n"
        f"Address: {address}\n"
        f"Check date: {due_iso[:10]}\n\n"
        "Review permit status, replacement planting records, and developer "
        "compliance to assess whether intervention is still required."
    )

    try:
        from app.services.notification_service import notify_guardian_check
        await notify_guardian_check(
            briefing_id=briefing_id,
            permit_id=permit_id,
            address=address,
            step=step,
            audit_report=audit_report,
            next_check=next_step,
            next_check_date=next_date,
        )
        logger.info("Guardian check email sent: briefing=%s step=%s", briefing_id, step)
    except Exception:
        logger.exception("Failed to send guardian check email: briefing=%s step=%s", briefing_id, step)
        return

    # Advance the pointer (or clear it when year5 is done)
    update: dict
    if next_step:
        update = {"$set": {"guardian_schedule.next_check": next_step}}
    else:
        update = {
            "$set": {"guardian_schedule.next_check": None, "guardian_schedule.closed_at": now_iso}
        }
    await db.briefings.update_one({"_id": doc["_id"]}, update)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    # Run at the top of every hour
    scheduler.add_job(run_guardian_checks, "interval", hours=1, id="guardian_checks", replace_existing=True)
    return scheduler
