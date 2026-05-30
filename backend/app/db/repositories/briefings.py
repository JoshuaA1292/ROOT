from datetime import datetime, timezone
from app.db.client import get_db, bson_clean


async def create_briefing(permit_id: str) -> str:
    db = get_db()
    briefing_id = f"brief_{permit_id}_v{int(datetime.now(timezone.utc).timestamp())}"
    await db.briefings.insert_one({
        "_id": briefing_id,
        "permit_id": permit_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "coalition_summary": None,
        "developer_snapshot": None,
        "precedent_refs": [],
        "policy_refs": [],
        "draft_comment": "",
        "citations": [],
        "status": "draft",
        "reviewed_by_email": None,
        "edits": [],
    })
    return briefing_id


async def get_briefing_by_id(briefing_id: str) -> dict | None:
    db = get_db()
    doc = await db.briefings.find_one({"_id": briefing_id})
    return bson_clean(doc) if doc else None


async def update_briefing(briefing_id: str, update_data: dict) -> None:
    db = get_db()
    await db.briefings.update_one({"_id": briefing_id}, {"$set": update_data})


async def get_latest_briefing_for_permit(permit_id: str) -> dict | None:
    db = get_db()
    cursor = db.briefings.find({"permit_id": permit_id}).sort("created_at", -1).limit(1)
    results = await cursor.to_list(length=1)
    return bson_clean(results[0]) if results else None
