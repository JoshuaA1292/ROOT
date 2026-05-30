"""
SSE stream endpoint — subscribes to events from a running briefing pipeline.

Flow:
  1. Client calls POST /briefings/{permit_id}/trigger → gets briefing_id
  2. Client opens GET /stream/briefings/{briefing_id} → receives SSE events
  3. Pipeline pushes events to asyncio.Queue keyed by briefing_id
  4. This endpoint drains the queue and forwards events to the client
"""
import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from app.agents.orchestrator import events_for_briefing
from app.db.repositories.briefings import get_briefing_by_id

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/briefings/{briefing_id}")
async def stream_briefing_events(briefing_id: str):
    """
    Subscribe to live agent pipeline events for a briefing.

    Streams server-sent events with named event types:
      permit_loaded, coalition_start/complete, developer_loaded,
      precedent_start/complete, briefing_start/complete, warning, error, done
    """
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail=f"Briefing {briefing_id} not found")

    async def event_generator():
        async for event in events_for_briefing(briefing_id):
            yield {
                "data": json.dumps({"event": event["event"], "data": event["data"]}),
            }

    return EventSourceResponse(event_generator())
