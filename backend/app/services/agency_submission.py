from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.db.repositories.briefings import update_briefing
from app.db.repositories.workspaces import get_briefing_export, mark_export_submitted


SUPPORTED_AGENCIES = {
    "nyc_parks": "NYC Parks",
    "community_board": "Community Board",
}


def agency_endpoint(agency_key: str) -> str:
    if agency_key == "nyc_parks":
        return settings.nyc_parks_submission_url
    if agency_key == "community_board":
        return settings.community_board_submission_url
    return ""


def normalize_agency(agency: str) -> str:
    return agency.strip().lower().replace(" ", "_")


async def submit_export(export_id: str, agency: str, submitter_email: str) -> dict:
    export = await get_briefing_export(export_id)
    if not export:
        raise ValueError(f"Export {export_id} not found")

    agency_key = normalize_agency(agency or export.get("agency", ""))
    if agency_key not in SUPPORTED_AGENCIES:
        raise ValueError(f"Unsupported agency submission target: {agency}")

    endpoint = agency_endpoint(agency_key)
    mode = "adapter_stub"
    external_reference = f"{agency_key}:{export_id}"

    if endpoint:
        headers = {"Content-Type": "application/json"}
        if settings.agency_submission_api_key:
            headers["Authorization"] = f"Bearer {settings.agency_submission_api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                endpoint,
                json={
                    "export_id": export_id,
                    "agency": SUPPORTED_AGENCIES[agency_key],
                    "submitter_email": submitter_email,
                    "content": export.get("content", ""),
                },
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json() if response.content else {}
        mode = "http_adapter"
        external_reference = payload.get("reference") or payload.get("id") or external_reference

    submission = {
        "agency": SUPPORTED_AGENCIES[agency_key],
        "submitted_by": submitter_email,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "submitted",
        "mode": mode,
        "external_reference": external_reference,
    }
    await mark_export_submitted(export_id, submission)
    await update_briefing(export["briefing_id"], {"status": "submitted"})
    return {"export_id": export_id, "submission": submission}
