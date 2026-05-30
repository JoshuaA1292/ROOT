"""Tests for auth enforcement, source config, and agency submission."""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from app.deps_auth import current_user_email, resolve_user_email
from app.services.agency_submission import normalize_agency, submit_export
from app.services.source_config import ingestion_source_status


@pytest.mark.asyncio
async def test_current_user_email_requires_header():
    with pytest.raises(HTTPException) as exc:
        await current_user_email(None)

    assert exc.value.status_code == 401


def test_normalize_agency_key():
    assert normalize_agency("NYC Parks") == "nyc_parks"


def test_resolve_user_email_supports_iap_header():
    assert resolve_user_email(
        x_goog_authenticated_user_email="accounts.google.com:tree@example.com",
        auth_mode="iap",
    ) == "tree@example.com"


@pytest.mark.asyncio
async def test_submit_export_marks_export_and_briefing_submitted():
    export = {"_id": "export_1", "briefing_id": "brief_1", "agency": "NYC Parks"}
    with (
        patch("app.services.agency_submission.get_briefing_export", new=AsyncMock(return_value=export)),
        patch("app.services.agency_submission.mark_export_submitted", new=AsyncMock()) as mark_export,
        patch("app.services.agency_submission.update_briefing", new=AsyncMock()) as update_briefing,
    ):
        result = await submit_export("export_1", "NYC Parks", "a@example.com")

    assert result["submission"]["external_reference"] == "nyc_parks:export_1"
    mark_export.assert_awaited_once()
    update_briefing.assert_awaited_once_with("brief_1", {"status": "submitted"})


@pytest.mark.asyncio
async def test_submit_export_uses_live_http_adapter_when_configured(monkeypatch):
    export = {
        "_id": "export_1",
        "briefing_id": "brief_1",
        "agency": "NYC Parks",
        "content": "comment",
    }

    class FakeResponse:
        content = b'{"reference":"parks-123"}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"reference": "parks-123"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    from app.services import agency_submission

    monkeypatch.setattr(agency_submission.settings, "nyc_parks_submission_url", "https://parks.example/submit")
    monkeypatch.setattr(agency_submission.httpx, "AsyncClient", lambda timeout: FakeClient())

    with (
        patch("app.services.agency_submission.get_briefing_export", new=AsyncMock(return_value=export)),
        patch("app.services.agency_submission.mark_export_submitted", new=AsyncMock()),
        patch("app.services.agency_submission.update_briefing", new=AsyncMock()),
    ):
        result = await submit_export("export_1", "NYC Parks", "a@example.com")

    assert result["submission"]["mode"] == "http_adapter"
    assert result["submission"]["external_reference"] == "parks-123"


def test_ingestion_source_status_reports_config(monkeypatch):
    from app.services import source_config

    monkeypatch.setattr(source_config.settings, "nyc_dob_permit_url", "https://example.com/dob")
    monkeypatch.setattr(source_config.settings, "parks_tree_work_url", "")

    status = ingestion_source_status()

    assert status["nyc_dob_permit_url"]["configured"] is True
    assert status["parks_tree_work_url"]["configured"] is False
    assert "portland_tree_inventory_url" in status
