from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


BriefingStatus = Literal["draft", "edited", "reviewed", "exported", "submitted"]


class CoalitionSummary(BaseModel):
    tree_count: int
    canopy_sqft: float
    stormwater_gal_yr: float
    co2_lbs_lifetime: float
    cooling_usd_yr: float
    total_ecosystem_usd_yr: float
    ej_tier: str  # "High" | "Medium" | "Low"
    heat_vulnerable_residents: int
    tree_ids: list[str]


class DeveloperSnapshot(BaseModel):
    developer_id: str
    name: str
    compliance_rate: float
    city_target: float = 0.85
    target_delta: float = 0.0
    permits_filed: int
    promised_replacements: int
    verified_surviving: int
    violations_count: int
    at_risk_replacements: int = 0


class PrecedentRef(BaseModel):
    id: str
    title: str
    outcome: str
    year: int
    similarity_score: float
    arguments_used: list[str]


class PolicyRef(BaseModel):
    id: str
    title: str
    section: str
    text_excerpt: str
    matched_tags: list[str]


class BriefingEdit(BaseModel):
    timestamp: str
    previous_text: str
    new_text: str


class BriefingDocument(BaseModel):
    id: str = Field(alias="_id")
    permit_id: str
    created_at: str
    coalition_summary: Optional[CoalitionSummary] = None
    developer_snapshot: Optional[DeveloperSnapshot] = None
    precedent_refs: list[PrecedentRef] = []
    policy_refs: list[PolicyRef] = []
    draft_comment: str = ""
    citations: list[str] = []
    status: BriefingStatus = "draft"
    reviewed_by_email: Optional[str] = None
    edits: list[BriefingEdit] = []

    model_config = {"populate_by_name": True}


class BriefingCreate(BaseModel):
    permit_id: str


class BriefingPatch(BaseModel):
    draft_comment: Optional[str] = None
    status: Optional[BriefingStatus] = None
    reviewed_by_email: Optional[str] = None
