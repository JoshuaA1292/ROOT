from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class GeoPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float]


class PermitDocument(BaseModel):
    id: str = Field(alias="_id")
    developer_id: str
    filed_date: str
    address: str
    project_type: str
    removal_radius_m: float
    center: GeoPoint
    stated_reason: str
    promised_replacements: int
    comment_deadline: str
    status: str  # open_for_comment | closed | approved | denied
    threatened_tree_ids: list[str] = []

    model_config = {"populate_by_name": True}
