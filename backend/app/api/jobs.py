from fastapi import APIRouter, Query

from app.agents.orchestrator import resume_pending_jobs, check_due_guardian_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/briefings/resume")
async def resume_briefing_jobs(limit: int = Query(10, ge=1, le=100)):
    return await resume_pending_jobs(limit)


@router.post("/guardian/check")
async def run_guardian_checks(limit: int = Query(25, ge=1, le=100)):
    """Find submitted briefings with overdue guardian checks and queue re-analysis jobs."""
    return await check_due_guardian_jobs(limit)
