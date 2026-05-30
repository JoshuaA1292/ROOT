import time
from fastapi import APIRouter

from app.services.source_config import ingestion_source_status
from app.config import settings
from app.db.access_mode import mongodb_access_mode

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/ingestion-sources")
async def get_ingestion_sources():
    return ingestion_source_status()


@router.get("/runtime")
async def get_runtime():
    """Judge Mode — returns agent mode, MongoDB operations, and Gemini model."""
    mcp_mode = mongodb_access_mode() == "mcp"
    adk_mode = bool(settings.google_cloud_project)
    return {
        "agent_mode": "ADK + Vertex AI" if adk_mode else "Direct Python pipeline (ADK fallback)",
        "gemini_model": settings.gemini_model or "gemini-2.0-flash",
        "draft_model": "Gemini",
        "mongodb_access_mode": mongodb_access_mode(),
        "mcp_active": mcp_mode,
        "google_cloud_project": settings.google_cloud_project or "(local)",
        "mongodb_operations": [
            "$geoWithin $centerSphere — coalition discovery",
            "Atlas Vector Search (768-dim) — precedent RAG",
            "$lookup + $facet + $unwind + $group — developer accountability",
            "$switch — risk tier classification",
            "$elemMatch — entity network cross-reference",
        ],
        "atlas_vector_search_index": "precedents_vector_index",
        "embedding_model": "text-embedding-004 (768 dimensions)",
        "corpus": {
            "trees": "1,019 seeded (NYC 2015 Street Tree Census; 683K full inventory available)",
            "permits": "15 active open-for-comment",
            "precedents": "30 cases with embeddings",
            "developers": "11 entities",
        },
        "server_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
