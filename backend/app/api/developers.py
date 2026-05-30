from fastapi import APIRouter, HTTPException
from app.db.repositories.developers import get_developer_by_id, list_developers
from app.db.repositories.developer_analytics import (
    get_developer_risk_intelligence,
    get_entity_network,
)
from app.services.planting_ingestion import ingest_planting_records
from app.services.reconciliation import reconcile_developer_ledgers

router = APIRouter(prefix="/developers", tags=["developers"])


@router.get("")
async def get_developers():
    devs = await list_developers()
    for d in devs:
        d["id"] = str(d.pop("_id"))
    return devs


@router.get("/{developer_id}")
async def get_developer(developer_id: str):
    dev = await get_developer_by_id(developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    dev["id"] = str(dev.pop("_id"))
    return dev


@router.get("/{developer_id}/ledger")
async def get_ledger(developer_id: str):
    dev = await get_developer_by_id(developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    dev["id"] = str(dev.pop("_id"))
    return dev


@router.get("/{developer_id}/risk-intelligence")
async def get_risk_intelligence(developer_id: str):
    """
    MongoDB $lookup + $facet aggregation pipeline — computes compliance trend,
    violation breakdown, active permit exposure, and risk tier in one round-trip.
    """
    result = await get_developer_risk_intelligence(developer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Developer not found")
    return result


@router.get("/{developer_id}/network")
async def get_developer_network(developer_id: str):
    """
    MongoDB $lookup + $group + $elemMatch aggregation — finds all permits
    filed under linked entity names and computes the true network-wide
    compliance rate across shell companies.
    """
    result = await get_entity_network(developer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Developer not found")
    return result


@router.post("/reconcile")
async def reconcile_ledgers(developer_id: str | None = None):
    return await reconcile_developer_ledgers(developer_id)


@router.post("/planting-records/ingest")
async def ingest_parks_planting_records(body: dict | None = None):
    body = body or {}
    return await ingest_planting_records(
        records=body.get("records"),
        source_url=body.get("source_url"),
        reconcile=body.get("reconcile", True),
    )
