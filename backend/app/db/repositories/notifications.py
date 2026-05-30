from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from app.db.client import get_db, bson_clean


async def create_notification(data: dict[str, Any]) -> str:
    db = get_db()
    data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    data.setdefault("read", False)
    result = await db.notifications.insert_one(data)
    return str(result.inserted_id)


async def list_notifications(limit: int = 20) -> list[dict]:
    db = get_db()
    cursor = db.notifications.find({}).sort("created_at", -1).limit(limit)
    out = []
    async for doc in cursor:
        doc = bson_clean(doc)
        doc["id"] = doc.pop("_id", str(doc.get("id", "")))
        out.append(doc)
    return out


async def mark_notification_read(notification_id: str) -> None:
    db = get_db()
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True}},
    )


async def count_unread() -> int:
    db = get_db()
    return await db.notifications.count_documents({"read": False})
