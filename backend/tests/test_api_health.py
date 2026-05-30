"""Integration-style tests for API endpoints — mocked MongoDB."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health():
    with patch("app.main.ping", new=AsyncMock(return_value=True)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_health_degraded_when_db_unreachable():
    with patch("app.main.ping", new=AsyncMock(return_value=False)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_trees_endpoint_bad_bbox():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/trees?bbox=bad")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_trees_endpoint_valid_bbox():
    mock_trees = [
        {
            "_id": "tree_100000",
            "species": {"common": "London Planetree"},
            "location": {"type": "Point", "coordinates": [-73.98, 40.69]},
            "health": "Good",
            "ecosystem_value_usd_yr": {"total_usd": 42.5},
        }
    ]
    with patch("app.api.trees.get_trees_in_bbox", new=AsyncMock(return_value=mock_trees)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/trees?bbox=-74.0,40.6,-73.9,40.75")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "tree_100000"
    assert data[0]["species"] == "London Planetree"


@pytest.mark.asyncio
async def test_permit_not_found():
    with patch("app.api.permits.get_permit_by_id", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/permits/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_permits_list():
    mock_permits = [
        {
            "_id": "permit_2026_0184",
            "developer_id": "dev_atlas_holdings",
            "filed_date": "2026-04-22",
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
    ]
    with (
        patch("app.api.permits.list_permits", new=AsyncMock(return_value=mock_permits)),
        patch("app.api.permits.get_trees_in_radius", new=AsyncMock(return_value=[])),
        patch("app.api.permits.get_developer_by_id", new=AsyncMock(return_value=None)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/permits?status=open_for_comment")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["id"] == "permit_2026_0184"


@pytest.mark.asyncio
async def test_patch_briefing_marks_text_edits_as_edited():
    briefing = {
        "_id": "brief_test",
        "permit_id": "permit_test",
        "created_at": "2026-05-26T00:00:00+00:00",
        "draft_comment": "original",
        "status": "draft",
        "edits": [],
        "citations": [],
        "precedent_refs": [],
        "policy_refs": [],
    }
    updated = {**briefing, "draft_comment": "revised", "status": "edited"}

    with (
        patch("app.api.briefings.get_briefing_by_id", new=AsyncMock(side_effect=[briefing, updated])),
        patch("app.api.briefings.update_briefing", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch("/briefings/brief_test", json={"draft_comment": "revised"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "edited"


@pytest.mark.asyncio
async def test_patch_briefing_rejects_invalid_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/briefings/brief_test", json={"status": "autofile"})

    assert resp.status_code == 422
