from fastapi import APIRouter, Query

from app.services.observability import get_pipeline_metrics
from app.db.repositories.quality_alerts import list_quality_alerts

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/agent-pipeline")
async def agent_pipeline_metrics(
    limit: int = Query(100, ge=1, le=1000),
    slow_threshold_seconds: float = Query(90.0, ge=1),
):
    return await get_pipeline_metrics(limit, slow_threshold_seconds)


@router.get("/alerts")
async def quality_alerts(status: str = "open", limit: int = Query(100, ge=1, le=1000)):
    alerts = await list_quality_alerts(status, limit)
    for alert in alerts:
        alert["id"] = str(alert.pop("_id"))
    return alerts
