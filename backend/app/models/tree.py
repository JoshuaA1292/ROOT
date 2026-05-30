from pydantic import BaseModel, Field
from typing import Optional


class Species(BaseModel):
    common: str
    latin: str


class EcosystemValue(BaseModel):
    stormwater_gal: float = 0
    stormwater_usd: float = 0
    co2_lbs: float = 0
    co2_usd: float = 0
    cooling_kwh: float = 0
    cooling_usd: float = 0
    air_quality_usd: float = 0
    total_usd: float = 0


class EJScore(BaseModel):
    heat_vuln_pct: float = 0  # 0-100 percentile
    tract_score: float = 0    # 0-1 normalized


class GeoPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float]  # [lng, lat]


class TreeDocument(BaseModel):
    id: str = Field(alias="_id")
    nyc_tree_id: int
    species: Species
    diameter_in: float
    health: str
    status: str
    location: GeoPoint
    address: str
    borough: str
    census_tract: str
    ecosystem_value_usd_yr: EcosystemValue
    ej_score: EJScore
    planted_year: Optional[int] = None
    last_inspection: Optional[str] = None

    model_config = {"populate_by_name": True}


class TreeSummary(BaseModel):
    """Lightweight version for map viewport responses."""
    id: str = Field(alias="_id")
    species_common: str
    location: GeoPoint
    health: str
    ecosystem_total_usd: float

    model_config = {"populate_by_name": True}
