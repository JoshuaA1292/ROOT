"""
ROOT ADK Agent — Google Agent Development Kit 2.x implementation.

Architecture:
  LlmAgent (Gemini as orchestrator) calls four FunctionTools:
    1. get_coalition_impact     → MongoDB $geoWithin + ecosystem aggregation
    2. get_developer_ledger     → MongoDB developer compliance lookup
    3. search_relevant_precedents → Atlas Vector Search RAG
    4. get_policy_references    → city canopy, heat, carbon, and replacement rules

  After all tools return, Gemini writes the public comment as its final response.
  That response is saved to the briefings collection by the pipeline wrapper.

The agent's per-tool callbacks push events to an asyncio.Queue so the SSE
endpoint can stream progress to the frontend in real time.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai import types as genai_types

from app.agents import coalition_agent, developer_ledger_agent, policy_agent
from app.db.repositories.permits import get_permit_by_id
from app.db.repositories.briefings import update_briefing
from app.db.repositories.precedents import vector_search_precedents
from app.db.access_mode import load_mongodb_mcp_config, use_mongodb_mcp
from app.models.briefing import CoalitionSummary, DeveloperSnapshot
from app.services.embeddings import embed_text
from app.config import settings

SYSTEM_INSTRUCTION = """\
You are ROOT's orchestration agent — a specialist in urban tree protection. Your job is to:

1. Call get_coalition_impact with the permit_id to identify all threatened trees and their \
combined ecosystem value (stormwater interception, carbon storage, cooling energy, air quality).

2. Call get_developer_ledger with the permit_id to retrieve the developer's documented \
replacement compliance history.

3. Call search_relevant_precedents with a plain-English summary of the permit context, \
coalition impact, and EJ tier to find the most relevant prior cases.

4. Call get_policy_references with the coalition impact and developer ledger results to \
retrieve the city canopy, heat resilience, carbon, and replacement rules that apply.

5. Using ALL the data returned by those four tools, write a complete, legally-grounded \
public comment letter. Structure it with these sections:
   - Opening Statement
   - Ecosystem Impact (with specific numbers)
   - Developer Compliance History
   - Relevant Precedents
   - Policy Contradictions
   - Requested Conditions (bulleted, enforceable)
   - Closing

Write the comment in a factual, formal tone. Cite exact numbers. Never use emotional language. \
End with a Citations & Data Sources appendix listing all references used.

You are the research department. The human is the voice.
"""



# ── Tool functions ───────────────────────────────────────────────────────────

async def get_coalition_impact(permit_id: str) -> dict[str, Any]:
    """Find all trees within the permit's impact radius and return their combined ecosystem value.

    Args:
        permit_id: The permit ID to analyze (e.g. permit_2026_0184).

    Returns:
        Dict with tree_count, canopy_sqft, stormwater_gal_yr, co2_lbs_lifetime,
        cooling_usd_yr, total_ecosystem_usd_yr, ej_tier, heat_vulnerable_residents,
        and tree_ids list.
    """
    permit = await get_permit_by_id(permit_id)
    if not permit:
        return {"error": f"Permit {permit_id} not found"}

    center = permit.get("center", {}).get("coordinates", [0, 0])
    coalition = await coalition_agent.run(
        permit_id=permit_id,
        center_lng=center[0],
        center_lat=center[1],
        radius_m=permit.get("removal_radius_m", 80),
    )
    return coalition.model_dump()


async def get_developer_ledger(permit_id: str) -> dict[str, Any]:
    """Get the developer's documented compliance history for this permit.

    Args:
        permit_id: The permit ID whose developer to look up.

    Returns:
        Dict with developer name, compliance_rate, permits_filed,
        promised_replacements, verified_surviving, and violations list.
    """
    permit = await get_permit_by_id(permit_id)
    if not permit:
        return {"error": f"Permit {permit_id} not found"}

    snapshot = await developer_ledger_agent.run_for_developer(permit.get("developer_id", ""))
    return snapshot.model_dump()


async def search_relevant_precedents(permit_context: str) -> list[dict[str, Any]]:
    """Search for prior permit cases most semantically similar to the current situation.

    Args:
        permit_context: Plain-English description of the permit: address, project type,
            removal reason, number of trees threatened, ecosystem value, EJ tier.

    Returns:
        List of up to 5 precedent cases with title, outcome, year, similarity_score,
        and arguments_used.
    """
    embedding = embed_text(permit_context[:4000])
    results = await vector_search_precedents(embedding, top_k=5)
    return [
        {
            "id": str(r["_id"]),
            "title": r.get("title", ""),
            "outcome": r.get("outcome", ""),
            "year": r.get("year", 0),
            "similarity_score": round(r.get("score", 0.0), 4),
            "arguments_used": r.get("arguments_used", []),
            "comment_excerpt": r.get("comment_text", "")[:400],
        }
        for r in results
    ]


async def get_policy_references(
    coalition_summary: dict[str, Any],
    developer_ledger: dict[str, Any],
) -> list[dict[str, Any]]:
    """Retrieve city policy references relevant to the impact and ledger findings.

    Args:
        coalition_summary: Result returned by get_coalition_impact.
        developer_ledger: Result returned by get_developer_ledger.

    Returns:
        List of policy references with title, section, excerpt, and matched tags.
    """
    coalition = CoalitionSummary(**coalition_summary)
    developer = DeveloperSnapshot(**developer_ledger)
    policies = await policy_agent.run(coalition, developer)
    return [p.model_dump() for p in policies]


# ── ADK Agent definition ─────────────────────────────────────────────────────

def build_agent() -> LlmAgent:
    """Build the ROOT LlmAgent. Called once per request context."""
    # Resolve and set GOOGLE_APPLICATION_CREDENTIALS to an absolute path if needed
    creds_path = settings.google_application_credentials
    if creds_path and not os.path.isabs(creds_path):
        creds_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", creds_path))
    if creds_path and os.path.exists(creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    # Use AI Studio key only when no service account credentials are found
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or not os.path.exists(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    ):
        studio_key = settings.google_ai_studio_key or settings.gemini_api_key
        if studio_key and not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = studio_key

    model = settings.gemini_model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    tools: list = [
        FunctionTool(get_coalition_impact),
        FunctionTool(get_developer_ledger),
        FunctionTool(search_relevant_precedents),
        FunctionTool(get_policy_references),
    ]

    if use_mongodb_mcp():
        mcp_config = load_mongodb_mcp_config()
        tools.append(MCPToolset(
            connection_params=StdioConnectionParams(
                command=mcp_config["command"],
                args=mcp_config.get("args", []),
                env=mcp_config.get("env", {}),
            )
        ))

    return LlmAgent(
        name="root_orchestrator",
        description="ROOT Urban Tree Intelligence Agent orchestrator",
        model=model,
        instruction=SYSTEM_INSTRUCTION,
        tools=tools,
    )


# ── Pipeline runner ───────────────────────────────────────────────────────────

TOOL_EVENT_LABELS = {
    "get_coalition_impact": "coalition",
    "get_developer_ledger": "developer",
    "search_relevant_precedents": "precedent",
    "get_policy_references": "policy",
}


_RETRYABLE_HTTP = {429, 500, 503}
_MAX_ADK_RETRIES = 3


def _exc_text(exc: Exception) -> str:
    parts = [str(exc), exc.__class__.__name__, exc.__class__.__module__]
    cause = getattr(exc, "__cause__", None)
    if cause:
        parts.extend([str(cause), cause.__class__.__name__, cause.__class__.__module__])
    return " ".join(parts).lower()


def _is_quota_exhausted(exc: Exception) -> bool:
    msg = _exc_text(exc)
    return any(
        kw in msg
        for kw in (
            "resource_exhausted",
            "resourceexhausted",
            "quota exceeded",
            "free_tier",
            "generaterequestsperday",
            "generate_content_free_tier_requests",
        )
    )


def _is_retryable(exc: Exception) -> bool:
    """True for transient Gemini/Vertex errors that are safe to retry."""
    if _is_quota_exhausted(exc):
        return True
    try:
        from google.genai.errors import ServerError, ClientError
        if isinstance(exc, (ServerError, ClientError)):
            return getattr(exc, "status_code", 0) in _RETRYABLE_HTTP
    except ImportError:
        pass
    msg = _exc_text(exc)
    return any(kw in msg for kw in ("503", "unavailable", "429", "rate limit", "high demand", "500"))


async def run_adk_pipeline(
    permit_id: str,
    briefing_id: str,
    event_queue: asyncio.Queue,
) -> str:
    """
    Run the ADK agent for a given permit.

    Pushes structured events into event_queue as the agent runs tools.
    Returns the final comment text from Gemini's response.
    Retries up to _MAX_ADK_RETRIES times on transient 429/500/503 errors
    before re-raising so the caller can fall back to the direct pipeline.
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_ADK_RETRIES):
        try:
            return await _run_adk_once(permit_id, briefing_id, event_queue)
        except Exception as exc:
            if not _is_retryable(exc):
                raise
            if _is_quota_exhausted(exc):
                await event_queue.put({
                    "event": "warning",
                    "data": {"message": "The Gemini API has been called too many times. Please try again later."},
                })
                raise
            last_exc = exc
            wait = 2.0 * (2 ** attempt)   # 2 s, 4 s, 8 s
            await event_queue.put({
                "event": "warning",
                "data": {"message": f"Gemini unavailable (attempt {attempt + 1}/{_MAX_ADK_RETRIES}), retrying in {wait:.0f}s…"},
            })
            await asyncio.sleep(wait)

    raise last_exc  # type: ignore[misc]


async def _run_adk_once(
    permit_id: str,
    briefing_id: str,
    event_queue: asyncio.Queue,
) -> str:
    """Single attempt at the ADK pipeline — called by run_adk_pipeline."""
    agent = build_agent()

    # Use callbacks to emit queue events at tool boundaries.
    # Accept **kwargs so the signature stays compatible across ADK versions.
    async def _before_tool(tool=None, args=None, **kwargs):
        if tool is None:
            return
        label = TOOL_EVENT_LABELS.get(tool.name, tool.name)
        await event_queue.put({
            "event": f"{label}_start",
            "data": {"tool": tool.name},
        })

    async def _after_tool(tool=None, args=None, **kwargs):
        if tool is None:
            return
        # ADK uses 'tool_response' in newer versions
        result = kwargs.get("tool_response") or kwargs.get("result")
        label = TOOL_EVENT_LABELS.get(tool.name, tool.name)
        data: dict = {"tool": tool.name}
        if isinstance(result, dict):
            if label == "coalition":
                data.update({
                    k: result.get(k)
                    for k in ("tree_count", "total_ecosystem_usd_yr", "ej_tier",
                              "stormwater_gal_yr", "canopy_sqft", "heat_vulnerable_residents")
                })
            elif label == "developer":
                data.update({
                    k: result.get(k)
                    for k in ("name", "compliance_rate", "permits_filed",
                              "promised_replacements", "verified_surviving",
                              "city_target", "target_delta", "at_risk_replacements")
                })
        elif isinstance(result, list) and label == "precedent":
            data["count"] = len(result)
        elif isinstance(result, list) and label == "policy":
            data["count"] = len(result)
            await update_briefing(briefing_id, {"policy_refs": result})
        await event_queue.put({"event": f"{label}_complete", "data": data})

    # Attach callbacks
    agent.before_tool_callback = _before_tool
    agent.after_tool_callback = _after_tool

    runner = InMemoryRunner(agent=agent, app_name="ROOT")

    user_msg = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=(
            f"Analyze permit {permit_id} and produce a complete public comment briefing. "
            f"Briefing record ID: {briefing_id}. "
            "Call all four tools in sequence, then write the full comment."
        ))],
    )

    session_svc: InMemorySessionService = runner.session_service
    session = await session_svc.create_session(
        app_name="ROOT",
        user_id="system",
    )

    final_text = ""

    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=user_msg,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts or []:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    return final_text
