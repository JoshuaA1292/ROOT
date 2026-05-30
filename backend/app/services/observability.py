from __future__ import annotations

from datetime import datetime

from app.db.repositories.briefing_jobs import list_recent_jobs


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def summarize_pipeline_jobs(jobs: list[dict], slow_threshold_seconds: float = 90.0) -> dict:
    by_status: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    durations: list[float] = []
    slow_jobs = 0

    for job in jobs:
        status = job.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        started = _parse_dt(job.get("started_at"))
        completed = _parse_dt(job.get("completed_at"))
        if started and completed:
            duration = (completed - started).total_seconds()
            durations.append(duration)
            if duration > slow_threshold_seconds:
                slow_jobs += 1

        for event in job.get("events", []):
            name = event.get("event", "unknown")
            event_counts[name] = event_counts.get(name, 0) + 1

    failed_jobs = by_status.get("failed", 0)
    return {
        "jobs_observed": len(jobs),
        "jobs_by_status": by_status,
        "events_by_type": event_counts,
        "error_events": event_counts.get("error", 0),
        "failed_jobs": failed_jobs,
        "slow_jobs": slow_jobs,
        "slow_threshold_seconds": slow_threshold_seconds,
        "alert_level": "critical" if failed_jobs else "warning" if slow_jobs else "ok",
        "avg_completed_duration_seconds": round(sum(durations) / len(durations), 3)
        if durations
        else None,
    }


async def get_pipeline_metrics(limit: int = 100, slow_threshold_seconds: float = 90.0) -> dict:
    return summarize_pipeline_jobs(await list_recent_jobs(limit), slow_threshold_seconds)
