"""
Outcome tracking — records what happened after a comment was submitted.
When a comment succeeds and conditions are imposed, ROOT updates the developer
ledger with the outcome so the compliance record reflects reality.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.client import get_db
from app.db.repositories.permits import get_permit_by_id

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


class OutcomePayload(BaseModel):
    permit_id: str
    briefing_id: str | None = None
    comment_acknowledged: bool = False
    conditions_imposed: list[str] = []    # e.g. ["surety_bond", "independent_audit"]
    replacements_required: int | None = None
    replacement_species: list[str] = []
    notes: str = ""
    reported_by: str = ""


@router.post("")
async def record_outcome(body: OutcomePayload):
    """Record what happened after a public comment was submitted."""
    db = get_db()

    permit = await get_permit_by_id(body.permit_id)
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    outcome = {
        "_id": f"outcome_{body.permit_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "permit_id": body.permit_id,
        "briefing_id": body.briefing_id,
        "comment_acknowledged": body.comment_acknowledged,
        "conditions_imposed": body.conditions_imposed,
        "replacements_required": body.replacements_required,
        "replacement_species": body.replacement_species,
        "notes": body.notes,
        "reported_by": body.reported_by,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.outcomes.insert_one(outcome)

    # If conditions were imposed, update the permit status
    if body.conditions_imposed:
        await db.permits.update_one(
            {"_id": body.permit_id},
            {"$set": {"status": "conditions_imposed", "outcome": outcome}},
        )

    # Update developer ledger: log this outcome so future compliance audits include it
    developer_id = permit.get("developer_id")
    if developer_id and body.comment_acknowledged:
        await db.developers.update_one(
            {"_id": developer_id},
            {
                "$push": {
                    "comment_outcomes": {
                        "permit_id": body.permit_id,
                        "conditions_imposed": body.conditions_imposed,
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                "$set": {"last_audit": datetime.now(timezone.utc).date().isoformat()},
            },
        )

    return {"status": "recorded", "permit_id": body.permit_id, "conditions": body.conditions_imposed}


@router.get("/{permit_id}")
async def get_outcome(permit_id: str):
    db = get_db()
    outcome = await db.outcomes.find_one({"permit_id": permit_id}, {"_id": 0})
    if not outcome:
        raise HTTPException(status_code=404, detail="No outcome recorded yet")
    return outcome


@router.post("/{permit_id}/verify")
async def verify_outcome_claim(permit_id: str, body: OutcomePayload):
    """
    Agent verifies whether the claimed outcome is plausible.
    Returns confidence score and any flags before the user saves.
    """
    from app.db.client import get_db as _get_db
    from app.services.verification_agent import verify_outcome
    from app.db.repositories.briefings import get_briefing_by_id

    db = _get_db()
    permit = await get_permit_by_id(permit_id)
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    developer_name = "Unknown Developer"
    compliance_rate = 0.5
    tree_count = 1

    if body.briefing_id:
        briefing = await get_briefing_by_id(body.briefing_id)
        if briefing:
            dev = briefing.get("developer_snapshot") or {}
            col = briefing.get("coalition_summary") or {}
            developer_name = dev.get("name", developer_name)
            compliance_rate = float(dev.get("compliance_rate", compliance_rate))
            tree_count = int(col.get("tree_count", tree_count))
    else:
        developer_id = permit.get("developer_id", "")
        if developer_id:
            dev_doc = await db.developers.find_one({"_id": developer_id})
            if dev_doc:
                developer_name = dev_doc.get("name", developer_name)
                promised = dev_doc.get("promised_replacements", 1)
                surviving = dev_doc.get("verified_surviving", 0)
                compliance_rate = surviving / promised if promised else 0.5

    result = await verify_outcome(
        permit_id=permit_id,
        briefing_id=body.briefing_id,
        comment_acknowledged=body.comment_acknowledged,
        conditions_imposed=body.conditions_imposed,
        notes=body.notes,
        developer_name=developer_name,
        compliance_rate=compliance_rate,
        tree_count=tree_count,
        address=permit.get("address", ""),
    )

    return result
