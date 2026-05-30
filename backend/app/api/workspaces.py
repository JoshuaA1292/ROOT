from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.repositories.workspaces import create_workspace, get_workspace, get_workspace_for_owner
from app.deps_auth import current_user_email
from app.services.agency_submission import submit_export
from app.services.exports import export_briefing_for_agency

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = "ROOT Workspace"
    owner_email: str | None = None


class BriefingExportRequest(BaseModel):
    briefing_id: str
    agency: str = "NYC Parks"
    workspace_name: str = "ROOT Workspace"
    workspace_id: str | None = None


class AgencySubmitRequest(BaseModel):
    export_id: str
    agency: str = "NYC Parks"


@router.post("")
async def create_resident_workspace(
    body: WorkspaceCreate,
    user_email: str = Depends(current_user_email),
):
    owner_email = body.owner_email or user_email
    if owner_email.lower() != user_email:
        raise HTTPException(status_code=403, detail="Cannot create workspace for another user")
    workspace_id = await create_workspace(body.name, owner_email)
    workspace = await get_workspace(workspace_id)
    workspace["id"] = str(workspace.pop("_id"))
    return workspace


@router.get("/{workspace_id}")
async def get_resident_workspace(
    workspace_id: str,
    user_email: str = Depends(current_user_email),
):
    workspace = await get_workspace_for_owner(workspace_id, user_email)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace["id"] = str(workspace.pop("_id"))
    return workspace


@router.post("/exports")
async def export_briefing(
    body: BriefingExportRequest,
    user_email: str = Depends(current_user_email),
):
    try:
        return await export_briefing_for_agency(
            body.briefing_id,
            user_email,
            body.agency,
            body.workspace_name,
            body.workspace_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/submissions")
async def submit_to_agency(
    body: AgencySubmitRequest,
    user_email: str = Depends(current_user_email),
):
    try:
        return await submit_export(body.export_id, body.agency, user_email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
