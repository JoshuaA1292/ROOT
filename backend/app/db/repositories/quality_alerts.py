from datetime import datetime, timezone
from app.db.client import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_quality_alert(kind: str, severity: str, subject_id: str, details: dict) -> str:
    db = get_db()
    alert_id = f"alert_{kind}_{subject_id}_{int(datetime.now(timezone.utc).timestamp())}"
    await db.quality_alerts.insert_one({
        "_id": alert_id,
        "kind": kind,
        "severity": severity,
        "subject_id": subject_id,
        "details": details,
        "status": "open",
        "created_at": _now(),
    })
    return alert_id


async def list_quality_alerts(status: str = "open", limit: int = 100) -> list[dict]:
    db = get_db()
    cursor = db.quality_alerts.find({"status": status}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
