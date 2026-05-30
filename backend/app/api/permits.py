from fastapi import APIRouter, HTTPException, Query
from app.db.repositories.permits import get_permit_by_id, list_permits
from app.db.repositories.trees import get_trees_in_radius
from app.db.repositories.developers import get_developer_by_id
from app.agents import coalition_agent
from app.services.permit_ingestion import ingest_permits

router = APIRouter(prefix="/permits", tags=["permits"])

ENFORCEMENT_THRESHOLD = 0.85


@router.get("")
async def get_permits(status: str | None = Query(None)):
    permits = await list_permits(status)
    for p in permits:
        center = p.get("center", {}).get("coordinates", [0, 0])
        radius = p.get("removal_radius_m", 100)
        nearby = await get_trees_in_radius(center[0], center[1], radius)
        p["threatened_tree_ids"] = [str(t["_id"]) for t in nearby]
        # Enforcement flag: mark permits from non-compliant developers
        dev_id = p.get("developer_id")
        if dev_id:
            dev = await get_developer_by_id(dev_id)
            if dev and dev.get("compliance_rate", 1.0) < ENFORCEMENT_THRESHOLD:
                p["enforcement_flag"] = True
                p["developer_compliance_rate"] = dev.get("compliance_rate")
        p["id"] = str(p.pop("_id"))
    return permits


@router.get("/{permit_id}")
async def get_permit(permit_id: str):
    permit = await get_permit_by_id(permit_id)
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")
    permit["id"] = str(permit.pop("_id"))
    return permit


@router.get("/{permit_id}/coalition")
async def get_coalition(permit_id: str):
    permit = await get_permit_by_id(permit_id)
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    center = permit.get("center", {}).get("coordinates", [0, 0])
    coalition = await coalition_agent.run(
        permit_id,
        center[0],
        center[1],
        permit.get("removal_radius_m", 100),
    )
    return coalition.model_dump()


@router.post("/ingest")
async def ingest_permit_records(body: dict | None = None):
    body = body or {}
    return await ingest_permits(
        records=body.get("records"),
        source_url=body.get("source_url"),
    )
