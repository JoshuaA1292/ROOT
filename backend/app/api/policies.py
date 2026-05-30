from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.policy_agent import run as match_policy_refs
from app.models.briefing import CoalitionSummary, DeveloperSnapshot

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyMatchRequest(BaseModel):
    coalition_summary: CoalitionSummary
    developer_ledger: DeveloperSnapshot


@router.post("/match")
async def match_policies(body: PolicyMatchRequest):
    policies = await match_policy_refs(body.coalition_summary, body.developer_ledger)
    return [p.model_dump() for p in policies]
