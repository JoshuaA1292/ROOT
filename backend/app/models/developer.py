from pydantic import BaseModel, Field
from typing import Optional


class Violation(BaseModel):
    permit_id: str
    type: str
    count: int
    year: int


class DeveloperDocument(BaseModel):
    id: str = Field(alias="_id")
    name: str
    permits_filed: int
    promised_replacements: int
    verified_surviving: int
    compliance_rate: float  # 0.0-1.0
    violations: list[Violation] = []
    linked_entities: list[str] = []
    last_audit: Optional[str] = None

    model_config = {"populate_by_name": True}
