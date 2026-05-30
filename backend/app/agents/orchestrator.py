"""
Orchestrator: entry point for the ROOT agent pipeline.

Strategy:
  1. If GOOGLE_CLOUD_PROJECT is configured → run the ADK pipeline (Gemini orchestrates tools)
  2. Fallback → direct Python pipeline (deterministic tool sequence, no Gemini orchestration)

Both paths push events to an asyncio.Queue so the SSE endpoint can stream
progress in real time without blocking.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.agents import (
    briefing_agent,
    coalition_agent,
    developer_ledger_agent,
    polish_agent,
    policy_agent,
    precedent_agent,
)
from app.db.repositories.permits import get_permit_by_id
from app.db.repositories.briefings import create_briefing, update_briefing
from app.db.repositories.briefing_jobs import (
    append_job_event,
    create_briefing_job,
    list_resumable_jobs,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
)
from app.models.briefing import CoalitionSummary, DeveloperSnapshot, PolicyRef, PrecedentRef
from app.config import settings


# ── Shared event queue registry ───────────────────────────────────────────────
# briefing_id → asyncio.Queue of event dicts
# Cleared when the pipeline completes or the SSE client disconnects.
_queues: dict[str, asyncio.Queue] = {}


def get_event_queue(briefing_id: str) -> asyncio.Queue:
    if briefing_id not in _queues:
        _queues[briefing_id] = asyncio.Queue()
    return _queues[briefing_id]


def release_event_queue(briefing_id: str) -> None:
    _queues.pop(briefing_id, None)


# ── Public API ────────────────────────────────────────────────────────────────

async def start_pipeline(permit_id: str) -> str:
    """
    Create a briefing record, launch the pipeline as a background task, and
    return the briefing_id immediately so the caller can subscribe to its queue.
    """
    briefing_id = await create_briefing(permit_id)
    await create_briefing_job(briefing_id, permit_id)
    get_event_queue(briefing_id)  # pre-create queue before task starts

    # Fire-and-forget background task
    asyncio.create_task(_run(permit_id, briefing_id))
    return briefing_id


_GUARDIAN_MILESTONES = ["day90", "month12", "month36", "year5"]


async def check_due_guardian_jobs(limit: int = 25) -> dict:
    """
    Find submitted briefings whose next guardian check date has passed,
    queue a re-analysis job for each, and advance their next_check pointer.
    Called daily by Cloud Scheduler.
    """
    from app.db.client import get_db

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    queued: list[str] = []
    cursor = db.briefings.find(
        {
            "status": "submitted",
            "guardian_schedule.next_check": {"$exists": True},
        }
    ).limit(limit)

    async for briefing in cursor:
        schedule = briefing.get("guardian_schedule", {})
        next_check = schedule.get("next_check")
        if not next_check or next_check not in _GUARDIAN_MILESTONES:
            continue
        check_due_at = schedule.get(next_check)
        if not check_due_at or check_due_at > now:
            continue

        briefing_id = str(briefing["_id"])
        permit_id = briefing.get("permit_id", "")
        await create_briefing_job(briefing_id + f"_{next_check}", permit_id)
        asyncio.create_task(_run(permit_id, briefing_id + f"_{next_check}"))

        # Advance next_check to the following milestone
        idx = _GUARDIAN_MILESTONES.index(next_check)
        next_milestone = _GUARDIAN_MILESTONES[idx + 1] if idx + 1 < len(_GUARDIAN_MILESTONES) else "complete"
        await db.briefings.update_one(
            {"_id": briefing["_id"]},
            {"$set": {f"guardian_schedule.{next_check}_status": "queued", "guardian_schedule.next_check": next_milestone}},
        )
        queued.append(briefing_id)

    return {"checked": len(queued), "briefing_ids": queued}


async def resume_pending_jobs(limit: int = 10) -> dict:
    """
    External-worker entrypoint. A Cloud Run job, Cloud Scheduler target, or
    Pub/Sub worker can call this to resume jobs persisted as queued/failed.
    """
    jobs = await list_resumable_jobs(limit)
    for job in jobs:
        asyncio.create_task(_run(job["permit_id"], job["briefing_id"]))
    return {
        "resumed": len(jobs),
        "briefing_ids": [job["briefing_id"] for job in jobs],
    }


async def events_for_briefing(briefing_id: str) -> AsyncGenerator[dict, None]:
    """
    Async generator that yields queued events for a briefing.
    Terminates on a sentinel None or an error event.
    """
    queue = get_event_queue(briefing_id)
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=120.0)
            if event is None:  # sentinel → pipeline finished
                return
            yield event
            if event.get("event") in ("error", "done"):
                return
    except asyncio.TimeoutError:
        yield {"event": "error", "data": {"message": "Pipeline timeout after 120s"}}
    finally:
        release_event_queue(briefing_id)


# ── Internal pipeline ─────────────────────────────────────────────────────────

def _is_transient_gemini_error(exc: Exception) -> bool:
    """True for 429/500/503 Gemini errors that warrant a direct-pipeline fallback."""
    try:
        from google.genai.errors import ServerError, ClientError
        if isinstance(exc, (ServerError, ClientError)):
            return getattr(exc, "status_code", 0) in {429, 500, 503}
    except ImportError:
        pass
    parts = [str(exc), exc.__class__.__name__, exc.__class__.__module__]
    cause = getattr(exc, "__cause__", None)
    if cause:
        parts.extend([str(cause), cause.__class__.__name__, cause.__class__.__module__])
    msg = " ".join(parts).lower()
    return any(
        kw in msg
        for kw in (
            "503", "unavailable", "429", "rate limit", "high demand", "500",
            "resource_exhausted", "resourceexhausted", "quota exceeded",
        )
    )


async def _run(permit_id: str, briefing_id: str) -> None:
    """Runs the full pipeline and pushes events to the briefing's queue."""
    queue = get_event_queue(briefing_id)

    try:
        await mark_job_running(briefing_id)
        if settings.google_cloud_project:
            try:
                await _run_adk(permit_id, briefing_id, queue)
            except Exception as adk_exc:
                if _is_transient_gemini_error(adk_exc):
                    await _emit(
                        briefing_id, queue, "warning",
                        {"message": "The Gemini API has been called too many times. Please try again later."},
                    )
                    await _run_direct(permit_id, briefing_id, queue)
                else:
                    raise
        else:
            await _run_direct(permit_id, briefing_id, queue)
        await mark_job_completed(briefing_id)
    except Exception as exc:
        event = {"event": "error", "data": {"message": str(exc)}}
        await append_job_event(briefing_id, event)
        await mark_job_failed(briefing_id, str(exc))
        await queue.put(event)
    finally:
        await queue.put(None)  # sentinel


async def _emit(briefing_id: str, queue: asyncio.Queue, event: str, data: dict) -> None:
    payload = {"event": event, "data": data}
    await append_job_event(briefing_id, payload)
    await queue.put(payload)


async def _run_adk(permit_id: str, briefing_id: str, queue: asyncio.Queue) -> None:
    """Pipeline using Google ADK — Gemini orchestrates the tool calls."""
    from app.agents.adk_agent import run_adk_pipeline
    from app.db.access_mode import use_mongodb_mcp

    await _emit(briefing_id, queue, "permit_loaded", {"mode": "adk", "permit_id": permit_id})

    if use_mongodb_mcp():
        await _emit(briefing_id, queue, "mcp_active", {
            "message": "MongoDB MCP toolset registered — Gemini will call Atlas collections via MCP protocol",
            "server": "@mongodb-js/mongodb-mcp-server",
            "mode": "mcp",
        })

    draft_comment = await run_adk_pipeline(permit_id, briefing_id, queue)

    if draft_comment:
        try:
            from app.db.repositories.briefings import get_briefing_by_id as _get_brief
            saved = await _get_brief(briefing_id) or {}
            permit = await get_permit_by_id(permit_id) or {}
            col_dict = saved.get("coalition_summary") or {}
            dev_dict = saved.get("developer_snapshot") or {}
            prec_dicts = saved.get("precedent_refs") or []
            pol_dicts = saved.get("policy_refs") or []
            if col_dict and dev_dict:
                draft_comment = polish_agent.run(
                    draft_comment,
                    permit,
                    CoalitionSummary(**col_dict),
                    DeveloperSnapshot(**dev_dict),
                    [PrecedentRef(**p) for p in prec_dicts],
                    [PolicyRef(**p) for p in pol_dicts],
                )
                await _emit(briefing_id, queue, "polish_complete", {"status": "release_ready"})
        except Exception as polish_exc:
            await _emit(briefing_id, queue, "warning", {"message": f"Release polish skipped: {polish_exc}"})

        # Extract citations section from the Gemini output
        citations: list[str] = []
        if "Citations & Data Sources" in draft_comment:
            parts = draft_comment.split("Citations & Data Sources")
            if len(parts) > 1:
                block = parts[1].strip().lstrip("#").strip()
                citations = [
                    ln.strip().lstrip("-").strip()
                    for ln in block.split("\n")
                    if ln.strip().startswith("-")
                ]

        await update_briefing(briefing_id, {
            "draft_comment": draft_comment,
            "citations": citations,
            "status": "draft",
        })

        try:
            from app.services.strategy import build_intervention_strategy, build_evidence_board
            from app.db.repositories.briefings import get_briefing_by_id as _get_brief
            saved = await _get_brief(briefing_id) or {}
            col_dict = saved.get("coalition_summary") or {}
            dev_dict = saved.get("developer_snapshot") or {}
            prec_dicts = saved.get("precedent_refs") or []
            pol_dicts  = saved.get("policy_refs") or []
            if col_dict and dev_dict:
                strategy = build_intervention_strategy(col_dict, dev_dict, prec_dicts, pol_dicts)
                evidence  = build_evidence_board(col_dict, dev_dict, prec_dicts, pol_dicts)
                await update_briefing(briefing_id, {
                    "intervention_strategy": strategy,
                    "evidence_board": evidence,
                })
        except Exception:
            pass

    await _emit(briefing_id, queue, "briefing_complete", {"briefing_id": briefing_id, "mode": "adk"})
    await _emit(briefing_id, queue, "done", {})


async def _run_direct(permit_id: str, briefing_id: str, queue: asyncio.Queue) -> None:
    """Direct Python pipeline — no Gemini orchestration, deterministic tool sequence."""
    await _emit(briefing_id, queue, "permit_loaded", {"mode": "direct", "permit_id": permit_id})

    permit = await get_permit_by_id(permit_id)
    if not permit:
        await _emit(briefing_id, queue, "error", {"message": f"Permit {permit_id} not found"})
        return

    center = permit.get("center", {}).get("coordinates", [0, 0])
    lng, lat = center[0], center[1]
    radius_m = permit.get("removal_radius_m", 100)

    # Coalition — reads trees collection via Atlas GeoSearch
    await _emit(briefing_id, queue, "atlas_read", {"collection": "trees", "op": "geoWithin", "via": "MongoDB Atlas"})
    await _emit(briefing_id, queue, "coalition_start", {})
    coalition = await coalition_agent.run(permit_id, lng, lat, radius_m)
    await update_briefing(briefing_id, {"coalition_summary": coalition.model_dump()})
    await _emit(briefing_id, queue, "coalition_complete", coalition.model_dump())

    # Developer ledger + Precedents (concurrent)
    await _emit(briefing_id, queue, "atlas_read", {"collection": "developers", "op": "findOne", "via": "MongoDB Atlas"})
    await _emit(briefing_id, queue, "precedent_start", {})
    prec_task = asyncio.create_task(precedent_agent.run(permit, coalition.model_dump()))
    developer = await developer_ledger_agent.run_for_developer(permit.get("developer_id", ""))
    await update_briefing(briefing_id, {"developer_snapshot": developer.model_dump()})
    await _emit(briefing_id, queue, "developer_loaded", developer.model_dump())

    await _emit(briefing_id, queue, "atlas_read", {"collection": "precedents", "op": "vectorSearch", "via": "Atlas Vector Search"})
    precedents = await prec_task
    await update_briefing(briefing_id, {"precedent_refs": [p.model_dump() for p in precedents]})
    await _emit(briefing_id, queue, "precedent_complete", {"count": len(precedents)})

    # Policy references
    await _emit(briefing_id, queue, "atlas_read", {"collection": "city_policies", "op": "find", "via": "MongoDB Atlas"})
    await _emit(briefing_id, queue, "policy_start", {})
    policies = await policy_agent.run(coalition, developer)
    await update_briefing(briefing_id, {"policy_refs": [p.model_dump() for p in policies]})
    await _emit(briefing_id, queue, "policy_complete", {"count": len(policies)})

    # Draft the comment via Gemini
    await _emit(briefing_id, queue, "gemini_start", {"model": settings.gemini_model or "gemini-2.0-flash", "task": "draft_public_comment"})
    await _emit(briefing_id, queue, "briefing_start", {})
    try:
        draft_comment, citations = await briefing_agent.run(
            permit, coalition, developer, precedents, policies,
        )
        await _emit(briefing_id, queue, "llm_complete", {"status": "ok"})
        await _emit(briefing_id, queue, "polish_complete", {"status": "release_ready"})
    except Exception as exc:
        msg = str(exc)
        if "too many times" in msg or "exhausted" in msg.lower():
            msg = "The Gemini API has been called too many times. Please try again later."
        draft_comment = polish_agent.run("", permit, coalition, developer, precedents, policies)
        citations = briefing_agent._extract_citations(draft_comment)
        await _emit(briefing_id, queue, "warning", {"message": f"{msg} Intervention drafted from structured evidence."})
        await _emit(briefing_id, queue, "polish_complete", {"status": "release_ready"})

    # Save draft first — always lands regardless of what follows
    await update_briefing(briefing_id, {
        "draft_comment": draft_comment,
        "citations": citations,
        "status": "draft",
    })

    # Build and save intervention strategy — wrapped so a bug here never kills the briefing
    try:
        from app.services.strategy import build_intervention_strategy, build_evidence_board
        prec_dicts = [p.model_dump() for p in precedents]
        pol_dicts  = [p.model_dump() for p in policies]
        col_dict   = coalition.model_dump()
        dev_dict   = developer.model_dump()
        strategy = build_intervention_strategy(col_dict, dev_dict, prec_dicts, pol_dicts)
        evidence  = build_evidence_board(col_dict, dev_dict, prec_dicts, pol_dicts)
        await update_briefing(briefing_id, {
            "intervention_strategy": strategy,
            "evidence_board": evidence,
        })
        await _emit(briefing_id, queue, "strategy_complete", {
            "recommended_action": strategy.get("recommended_action", ""),
            "confidence": strategy.get("confidence", ""),
            "developer_risk_tier": strategy.get("developer_risk_tier", ""),
        })
    except Exception as strategy_exc:
        await _emit(briefing_id, queue, "warning", {"message": f"Strategy computation failed: {strategy_exc}"})

    await _emit(briefing_id, queue, "briefing_complete", {"briefing_id": briefing_id, "mode": "direct"})
    await _emit(briefing_id, queue, "done", {})


