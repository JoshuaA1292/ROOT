from fastapi import APIRouter
from app.db.repositories.notifications import (
    list_notifications,
    mark_notification_read,
    count_unread,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(limit: int = 20):
    items = await list_notifications(limit)
    unread = await count_unread()
    return {"notifications": items, "unread_count": unread}


@router.post("/{notification_id}/read")
async def read_notification(notification_id: str):
    await mark_notification_read(notification_id)
    return {"status": "ok"}
