"""Tests for the orchestrator event queue and direct pipeline."""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.agents.orchestrator import start_pipeline, events_for_briefing, get_event_queue
from app.models.briefing import PolicyRef


MOCK_PERMIT = {
    "_id": "permit_test_001",
    "developer_id": "dev_atlas_holdings",
    "address": "487 Atlantic Ave, Brooklyn",
    "project_type": "mixed_use_tower",
    "removal_radius_m": 80,
    "center": {"type": "Point", "coordinates": [-73.9845, 40.6862]},
    "stated_reason": "Foundation work",
    "promised_replacements": 12,
    "comment_deadline": "2026-06-25",
    "status": "open_for_comment",
    "threatened_tree_ids": [],
}

MOCK_DEV = {
    "_id": "dev_atlas_holdings",
    "name": "Atlas Holdings LLC",
    "permits_filed": 3,
    "promised_replacements": 31,
    "verified_surviving": 14,
    "compliance_rate": 0.45,
    "violations": [{"permit_id": "p1", "type": "missing_replacement", "count": 3, "year": 2022}],
    "linked_entities": [],
}

MOCK_POLICIES = [
    PolicyRef(
        id="policy_onenyc_2050_canopy",
        title="OneNYC 2050 — Urban Forest Strategy",
        section="Strategy 6",
        text_excerpt="New York City commits to achieving 30% canopy coverage citywide by 2035.",
        matched_tags=["canopy_target"],
    )
]


@pytest.mark.asyncio
async def test_start_pipeline_returns_briefing_id():
    """start_pipeline should immediately return a briefing_id and create a queue."""
    with (
        patch("app.agents.orchestrator.create_briefing", new=AsyncMock(return_value="brief_test_001")),
        patch("app.agents.orchestrator.create_briefing_job", new=AsyncMock()),
        patch("app.agents.orchestrator._run", new=Mock(return_value="task")),
        patch("app.agents.orchestrator.asyncio.create_task"),
        patch("app.agents.orchestrator.settings") as mock_settings,
    ):
        mock_settings.google_cloud_project = ""
        briefing_id = await start_pipeline("permit_test_001")

    assert briefing_id == "brief_test_001"


@pytest.mark.asyncio
async def test_direct_pipeline_emits_expected_events():
    """Direct pipeline should emit coalition, developer, precedent, briefing events."""
    from app.agents.orchestrator import _run_direct
    from app.models.briefing import CoalitionSummary, PrecedentRef
    import asyncio

    mock_coalition = CoalitionSummary(
        tree_count=14,
        canopy_sqft=2800,
        stormwater_gal_yr=87400,
        co2_lbs_lifetime=152600,
        cooling_usd_yr=1820,
        total_ecosystem_usd_yr=4200,
        ej_tier="High",
        heat_vulnerable_residents=340,
        tree_ids=["tree_001"] * 14,
    )

    mock_precedents = [
        PrecedentRef(
            id="prec_0001",
            title="Brooklyn Heights 2022",
            outcome="permit_modified",
            year=2022,
            similarity_score=0.91,
            arguments_used=["stormwater_load"],
        )
    ]

    queue: asyncio.Queue = asyncio.Queue()

    with (
        patch("app.agents.orchestrator.get_permit_by_id", new=AsyncMock(return_value=MOCK_PERMIT)),
        patch("app.agents.developer_ledger_agent.get_developer_by_id", new=AsyncMock(return_value=MOCK_DEV)),
        patch("app.agents.orchestrator.coalition_agent.run", new=AsyncMock(return_value=mock_coalition)),
        patch("app.agents.orchestrator.precedent_agent.run", new=AsyncMock(return_value=mock_precedents)),
        patch("app.agents.orchestrator.policy_agent.run", new=AsyncMock(return_value=MOCK_POLICIES)),
        patch("app.agents.orchestrator.briefing_agent.run", new=AsyncMock(return_value=("draft text", ["cite1"]))),
        patch("app.agents.orchestrator.update_briefing", new=AsyncMock()),
        patch("app.agents.orchestrator.append_job_event", new=AsyncMock()),
    ):
        await _run_direct("permit_test_001", "brief_test_001", queue)

    # Collect all events from queue
    events = []
    while not queue.empty():
        e = queue.get_nowait()
        if e is not None:
            events.append(e["event"])

    assert "permit_loaded" in events
    assert "coalition_start" in events
    assert "coalition_complete" in events
    assert "developer_loaded" in events
    assert "precedent_complete" in events
    assert "policy_complete" in events
    assert "polish_complete" in events
    assert "briefing_complete" in events
    assert "done" in events


@pytest.mark.asyncio
async def test_direct_pipeline_uses_placeholder_when_gemini_unavailable():
    """When Gemini raises, the release polish agent should generate a complete filing."""
    from app.agents.orchestrator import _run_direct
    from app.models.briefing import CoalitionSummary
    import asyncio

    mock_coalition = CoalitionSummary(
        tree_count=5,
        canopy_sqft=600,
        stormwater_gal_yr=15000,
        co2_lbs_lifetime=30000,
        cooling_usd_yr=500,
        total_ecosystem_usd_yr=1200,
        ej_tier="Medium",
        heat_vulnerable_residents=0,
        tree_ids=["t1"] * 5,
    )

    saved_drafts = []

    async def fake_update(briefing_id, data):
        if "draft_comment" in data:
            saved_drafts.append(data["draft_comment"])

    with (
        patch("app.agents.orchestrator.get_permit_by_id", new=AsyncMock(return_value=MOCK_PERMIT)),
        patch("app.agents.developer_ledger_agent.get_developer_by_id", new=AsyncMock(return_value=MOCK_DEV)),
        patch("app.agents.orchestrator.coalition_agent.run", new=AsyncMock(return_value=mock_coalition)),
        patch("app.agents.orchestrator.precedent_agent.run", new=AsyncMock(return_value=[])),
        patch("app.agents.orchestrator.policy_agent.run", new=AsyncMock(return_value=MOCK_POLICIES)),
        patch("app.agents.orchestrator.briefing_agent.run", side_effect=RuntimeError("No Gemini credentials")),
        patch("app.agents.orchestrator.update_briefing", side_effect=fake_update),
        patch("app.agents.orchestrator.append_job_event", new=AsyncMock()),
    ):
        queue: asyncio.Queue = asyncio.Queue()
        await _run_direct("permit_test_001", "brief_test_001", queue)

    assert len(saved_drafts) == 1
    assert "PLACEHOLDER" not in saved_drafts[0]
    assert "### 7. Closing" not in saved_drafts[0]
    assert "CITATIONS & DATA SOURCES" in saved_drafts[0]
    assert "Atlas Holdings" in saved_drafts[0]


@pytest.mark.asyncio
async def test_briefing_trigger_api():
    """POST /briefings should return briefing_id immediately."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    with (
        patch("app.api.briefings.start_pipeline", new=AsyncMock(return_value="brief_xyz_001")),
        patch("app.api.briefings.get_latest_briefing_for_permit", new=AsyncMock(return_value=None)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/briefings", json={"permit_id": "permit_2026_0184"})

    assert resp.status_code == 200
    assert resp.json()["briefing_id"] == "brief_xyz_001"
    assert resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_briefing_trigger_requires_permit_id():
    """POST /briefings without permit_id should 400."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/briefings", json={})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_pending_jobs_launches_resumable_jobs():
    from app.agents.orchestrator import resume_pending_jobs

    jobs = [
        {"briefing_id": "brief_1", "permit_id": "permit_1"},
        {"briefing_id": "brief_2", "permit_id": "permit_2"},
    ]

    with (
        patch("app.agents.orchestrator.list_resumable_jobs", new=AsyncMock(return_value=jobs)),
        patch("app.agents.orchestrator._run", new=Mock(return_value="task")),
        patch("app.agents.orchestrator.asyncio.create_task") as create_task,
    ):
        result = await resume_pending_jobs(limit=2)

    assert result == {"resumed": 2, "briefing_ids": ["brief_1", "brief_2"]}
    assert create_task.call_count == 2
