"""Tests for durable briefing job repository helpers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.repositories import briefing_jobs


@pytest.mark.asyncio
async def test_create_briefing_job_writes_queued_record():
    db = MagicMock()
    db.briefing_jobs.insert_one = AsyncMock()

    with patch("app.db.repositories.briefing_jobs.get_db", return_value=db):
        await briefing_jobs.create_briefing_job("brief_1", "permit_1")

    record = db.briefing_jobs.insert_one.await_args.args[0]
    assert record["_id"] == "brief_1"
    assert record["permit_id"] == "permit_1"
    assert record["status"] == "queued"
    assert record["events"] == []


@pytest.mark.asyncio
async def test_append_job_event_persists_event_payload():
    db = MagicMock()
    db.briefing_jobs.update_one = AsyncMock()

    with patch("app.db.repositories.briefing_jobs.get_db", return_value=db):
        await briefing_jobs.append_job_event("brief_1", {"event": "done", "data": {}})

    update = db.briefing_jobs.update_one.await_args.args[1]
    assert update["$push"]["events"]["event"] == "done"
    assert "timestamp" in update["$push"]["events"]
