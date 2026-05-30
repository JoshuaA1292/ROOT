from datetime import datetime, timezone
from app.db.client import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_workspace(name: str, owner_email: str) -> str:
    db = get_db()
    workspace_id = f"workspace_{owner_email.lower().replace('@', '_at_').replace('.', '_')}"
    await db.resident_workspaces.update_one(
        {"_id": workspace_id},
        {
            "$set": {"name": name, "owner_email": owner_email, "updated_at": _now()},
            "$setOnInsert": {"_id": workspace_id, "created_at": _now(), "briefing_ids": []},
        },
        upsert=True,
    )
    return workspace_id


async def add_briefing_to_workspace(workspace_id: str, briefing_id: str) -> None:
    db = get_db()
    await db.resident_workspaces.update_one(
        {"_id": workspace_id},
        {"$addToSet": {"briefing_ids": briefing_id}, "$set": {"updated_at": _now()}},
    )


async def get_workspace(workspace_id: str) -> dict | None:
    db = get_db()
    return await db.resident_workspaces.find_one({"_id": workspace_id})


async def get_workspace_for_owner(workspace_id: str, owner_email: str) -> dict | None:
    db = get_db()
    return await db.resident_workspaces.find_one({
        "_id": workspace_id,
        "owner_email": owner_email,
    })


async def create_briefing_export(
    briefing_id: str,
    workspace_id: str,
    agency: str,
    content: str,
) -> str:
    db = get_db()
    export_id = f"export_{briefing_id}_{agency.lower().replace(' ', '_')}"
    await db.briefing_exports.update_one(
        {"_id": export_id},
        {
            "$set": {
                "briefing_id": briefing_id,
                "workspace_id": workspace_id,
                "agency": agency,
                "content": content,
                "status": "exported",
                "updated_at": _now(),
            },
            "$setOnInsert": {"_id": export_id, "created_at": _now()},
        },
        upsert=True,
    )
    return export_id


async def get_briefing_export(export_id: str) -> dict | None:
    db = get_db()
    return await db.briefing_exports.find_one({"_id": export_id})


async def mark_export_submitted(export_id: str, submission: dict) -> None:
    db = get_db()
    await db.briefing_exports.update_one(
        {"_id": export_id},
        {
            "$set": {
                "status": "submitted",
                "submission": submission,
                "updated_at": _now(),
            }
        },
    )
