from datetime import datetime, timezone
from app.db.client import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record_ingestion_run(kind: str, source: str, result: dict) -> str:
    db = get_db()
    run_id = f"ingest_{kind}_{int(datetime.now(timezone.utc).timestamp())}"
    await db.ingestion_runs.insert_one({
        "_id": run_id,
        "kind": kind,
        "source": source,
        "result": result,
        "created_at": _now(),
    })
    return run_id
