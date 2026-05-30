from datetime import datetime, timezone
from app.db.client import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_briefing_job(briefing_id: str, permit_id: str) -> None:
    db = get_db()
    await db.briefing_jobs.insert_one({
        "_id": briefing_id,
        "briefing_id": briefing_id,
        "permit_id": permit_id,
        "status": "queued",
        "attempts": 0,
        "created_at": _now(),
        "updated_at": _now(),
        "started_at": None,
        "completed_at": None,
        "last_error": None,
        "events": [],
    })


async def mark_job_running(briefing_id: str) -> None:
    db = get_db()
    await db.briefing_jobs.update_one(
        {"_id": briefing_id},
        {
            "$set": {
                "status": "running",
                "started_at": _now(),
                "updated_at": _now(),
                "last_error": None,
            },
            "$inc": {"attempts": 1},
        },
    )


async def append_job_event(briefing_id: str, event: dict) -> None:
    db = get_db()
    await db.briefing_jobs.update_one(
        {"_id": briefing_id},
        {
            "$push": {"events": {**event, "timestamp": _now()}},
            "$set": {"updated_at": _now()},
        },
    )


async def mark_job_completed(briefing_id: str) -> None:
    db = get_db()
    await db.briefing_jobs.update_one(
        {"_id": briefing_id},
        {"$set": {"status": "completed", "completed_at": _now(), "updated_at": _now()}},
    )


async def mark_job_failed(briefing_id: str, message: str) -> None:
    db = get_db()
    await db.briefing_jobs.update_one(
        {"_id": briefing_id},
        {"$set": {"status": "failed", "last_error": message, "updated_at": _now()}},
    )


async def get_briefing_job(briefing_id: str) -> dict | None:
    db = get_db()
    return await db.briefing_jobs.find_one({"_id": briefing_id})


async def list_resumable_jobs(limit: int = 10) -> list[dict]:
    db = get_db()
    cursor = (
        db.briefing_jobs
        .find({"status": {"$in": ["queued", "failed"]}})
        .sort("created_at", 1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def list_recent_jobs(limit: int = 100) -> list[dict]:
    db = get_db()
    cursor = db.briefing_jobs.find({}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
