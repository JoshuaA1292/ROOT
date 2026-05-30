from pydantic import BaseModel, Field
from typing import Optional


class PrecedentDocument(BaseModel):
    id: str = Field(alias="_id")
    title: str
    outcome: str  # permit_modified | denied | approved
    year: int
    borough: str
    trees_saved: int
    arguments_used: list[str]
    comment_text: str
    citations: list[str] = []
    source_url: Optional[str] = None
    # embedding stored in MongoDB but not returned in API responses

    model_config = {"populate_by_name": True}
