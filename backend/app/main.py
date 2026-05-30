from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/ regardless of where the server is started from
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path, override=False)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.db.client import close_client, ping
from app.api import (
    trees,
    permits,
    developers,
    briefings,
    stream,
    precedents,
    policies,
    jobs,
    workspaces,
    metrics,
    config,
    outcomes,
    sources,
    notifications,
    admin,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    try:
        from app.services.guardian_scheduler import create_scheduler
        scheduler = create_scheduler()
        scheduler.start()
    except Exception as _sched_err:
        import logging
        logging.getLogger(__name__).warning("Guardian scheduler not started: %s", _sched_err)
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        await close_client()


app = FastAPI(
    title="ROOT API",
    description="Urban Tree Intelligence Agent — backend service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Catch any Vercel preview / production deployment without hardcoding the URL.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trees.router)
app.include_router(permits.router)
app.include_router(developers.router)
app.include_router(briefings.router)
app.include_router(stream.router)
app.include_router(precedents.router)
app.include_router(policies.router)
app.include_router(jobs.router)
app.include_router(workspaces.router)
app.include_router(metrics.router)
app.include_router(config.router)
app.include_router(outcomes.router)
app.include_router(sources.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def mongodb_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch unhandled MongoDB connection errors and return a 503 with a diagnostic
    message instead of crashing the ASGI server.
    """
    msg = str(exc)
    if any(kw in msg for kw in ("ServerSelectionTimeout", "SSL handshake", "TLSV1", "Authentication failed", "not authorized")):
        hint = (
            "MongoDB Atlas connection failed. "
            "Check: (1) your IP is whitelisted in Atlas Network Access, "
            "(2) the cluster is not paused, "
            "(3) MONGODB_URI credentials in .env are correct."
        )
        return JSONResponse(status_code=503, content={"error": "database_unavailable", "hint": hint, "detail": msg[:200]})
    # Re-raise anything else as a generic 500
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": msg[:200]})


@app.get("/health")
async def health():
    db_ok = await ping()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "ROOT API",
        "database": "connected" if db_ok else "unreachable — check Atlas IP whitelist and cluster status",
    }
