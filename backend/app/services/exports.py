from app.db.repositories.briefings import get_briefing_by_id, update_briefing
from app.db.repositories.workspaces import (
    add_briefing_to_workspace,
    create_briefing_export,
    create_workspace,
    get_briefing_export,
    get_workspace,
    get_workspace_for_owner,
)


def build_agency_export_content(briefing: dict, agency: str) -> str:
    draft = briefing.get("draft_comment", "").strip()
    citations = briefing.get("citations", [])
    citation_block = "\n".join(f"- {citation}" for citation in citations)
    return (
        f"Agency: {agency}\n"
        f"Permit ID: {briefing.get('permit_id')}\n"
        f"Briefing ID: {briefing.get('_id')}\n\n"
        f"{draft}\n\n"
        "Citations\n"
        f"{citation_block or '- No citations recorded.'}\n"
    )


async def export_briefing_for_agency(
    briefing_id: str,
    owner_email: str,
    agency: str,
    workspace_name: str = "ROOT Workspace",
    workspace_id: str | None = None,
) -> dict:
    briefing = await get_briefing_by_id(briefing_id)
    if not briefing:
        raise ValueError(f"Briefing {briefing_id} not found")

    if workspace_id:
        workspace = await get_workspace_for_owner(workspace_id, owner_email)
        if not workspace:
            raise PermissionError("Workspace not found for current user")
    else:
        workspace_id = await create_workspace(workspace_name, owner_email)
    await add_briefing_to_workspace(workspace_id, briefing_id)
    content = build_agency_export_content(briefing, agency)
    export_id = await create_briefing_export(briefing_id, workspace_id, agency, content)
    await update_briefing(briefing_id, {"status": "exported"})
    export_doc = await get_briefing_export(export_id)
    workspace = await get_workspace(workspace_id)
    if workspace:
        workspace = {**workspace, "id": str(workspace["_id"])}
        workspace.pop("_id", None)
    if export_doc:
        export_doc = {**export_doc, "id": str(export_doc["_id"])}
        export_doc.pop("_id", None)

    return {
        "workspace": workspace,
        "export": export_doc,
    }
