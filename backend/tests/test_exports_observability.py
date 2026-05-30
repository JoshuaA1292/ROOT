"""Tests for resident exports and pipeline metrics."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.exports import build_agency_export_content, export_briefing_for_agency
from app.services.observability import summarize_pipeline_jobs
from app.services.quality import evaluate_briefing_quality, score_briefing_quality


def test_build_agency_export_content_includes_comment_and_citations():
    content = build_agency_export_content(
        {
            "_id": "brief_1",
            "permit_id": "permit_1",
            "draft_comment": "Please require replacement verification.",
            "citations": ["NYC Parks Rule 1-04"],
        },
        "NYC Parks",
    )

    assert "Agency: NYC Parks" in content
    assert "Please require replacement verification." in content
    assert "- NYC Parks Rule 1-04" in content


@pytest.mark.asyncio
async def test_export_briefing_for_agency_creates_workspace_and_export():
    briefing = {
        "_id": "brief_1",
        "permit_id": "permit_1",
        "draft_comment": "Draft",
        "citations": [],
    }
    workspace = {"_id": "workspace_a", "owner_email": "a@example.com", "briefing_ids": ["brief_1"]}
    export = {"_id": "export_1", "briefing_id": "brief_1", "status": "exported"}

    with (
        patch("app.services.exports.get_briefing_by_id", new=AsyncMock(return_value=briefing)),
        patch("app.services.exports.create_workspace", new=AsyncMock(return_value="workspace_a")),
        patch("app.services.exports.add_briefing_to_workspace", new=AsyncMock()),
        patch("app.services.exports.create_briefing_export", new=AsyncMock(return_value="export_1")),
        patch("app.services.exports.update_briefing", new=AsyncMock()),
        patch("app.services.exports.get_briefing_export", new=AsyncMock(return_value=export)),
        patch("app.services.exports.get_workspace", new=AsyncMock(return_value=workspace)),
    ):
        result = await export_briefing_for_agency("brief_1", "a@example.com", "NYC Parks")

    assert result["workspace"]["id"] == "workspace_a"
    assert result["export"]["id"] == "export_1"


def test_summarize_pipeline_jobs_counts_status_events_and_duration():
    metrics = summarize_pipeline_jobs([
        {
            "status": "completed",
            "started_at": "2026-05-27T00:00:00+00:00",
            "completed_at": "2026-05-27T00:00:05+00:00",
            "events": [{"event": "coalition_complete"}, {"event": "done"}],
        },
        {
            "status": "failed",
            "events": [{"event": "error"}],
        },
    ])

    assert metrics["jobs_observed"] == 2
    assert metrics["jobs_by_status"] == {"completed": 1, "failed": 1}
    assert metrics["events_by_type"]["done"] == 1
    assert metrics["error_events"] == 1
    assert metrics["failed_jobs"] == 1
    assert metrics["alert_level"] == "critical"
    assert metrics["avg_completed_duration_seconds"] == 5


def test_score_briefing_quality_rewards_grounded_drafts():
    result = score_briefing_quality({
        "draft_comment": (
            "Opening Statement\nEcosystem Impact\nDeveloper Compliance\n"
            "Policy Contradictions\nRequested Conditions"
        ),
        "citations": ["NYC Parks Rule 1-04"],
        "policy_refs": [{"id": "policy_1"}],
        "precedent_refs": [{"id": "prec_1"}],
    })

    assert result["score"] == 100
    assert result["checks"]["has_policy_refs"] is True


@pytest.mark.asyncio
async def test_evaluate_briefing_quality_creates_alert_for_low_score():
    with (
        patch("app.services.quality.get_briefing_by_id", new=AsyncMock(return_value={"_id": "brief_1", "draft_comment": ""})),
        patch("app.services.quality.create_quality_alert", new=AsyncMock(return_value="alert_1")),
    ):
        result = await evaluate_briefing_quality("brief_1", min_score=75)

    assert result["score"] < 75
    assert result["alert_id"] == "alert_1"
