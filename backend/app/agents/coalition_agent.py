"""
Coalition Agent: finds all trees within a permit's impact radius and aggregates
their combined ecosystem services into a single coalition impact report.
"""
from app.db.repositories.trees import get_trees_in_radius
from app.db.repositories.permits import update_permit_threatened_trees
from app.models.briefing import CoalitionSummary


# Rough canopy area per diameter inch (sq ft) based on NYC urban forestry data
CANOPY_SQFT_PER_DIAMETER_IN = 12.0

EJ_THRESHOLDS = {"High": 66, "Medium": 33, "Low": 0}

# Estimated residents per square mile in high-density NYC census tracts
RESIDENTS_PER_TREE_HIGH_EJ = 45


async def run(permit_id: str, center_lng: float, center_lat: float, radius_m: float) -> CoalitionSummary:
    trees = await get_trees_in_radius(center_lng, center_lat, radius_m)

    if not trees:
        return CoalitionSummary(
            tree_count=0,
            canopy_sqft=0,
            stormwater_gal_yr=0,
            co2_lbs_lifetime=0,
            cooling_usd_yr=0,
            total_ecosystem_usd_yr=0,
            ej_tier="Low",
            heat_vulnerable_residents=0,
            tree_ids=[],
        )

    tree_ids = [str(t["_id"]) for t in trees]
    await update_permit_threatened_trees(permit_id, tree_ids)

    total_stormwater = sum(t.get("ecosystem_value_usd_yr", {}).get("stormwater_gal", 0) for t in trees)
    total_co2 = sum(t.get("ecosystem_value_usd_yr", {}).get("co2_lbs", 0) * 50 for t in trees)  # ~50yr lifetime
    total_cooling = sum(t.get("ecosystem_value_usd_yr", {}).get("cooling_usd", 0) for t in trees)
    total_ecosystem = sum(t.get("ecosystem_value_usd_yr", {}).get("total_usd", 0) for t in trees)

    total_canopy = sum(
        t.get("diameter_in", 10) * CANOPY_SQFT_PER_DIAMETER_IN for t in trees
    )

    ej_scores = [t.get("ej_score", {}).get("heat_vuln_pct", 0) for t in trees]
    avg_ej = sum(ej_scores) / len(ej_scores) if ej_scores else 0
    if avg_ej >= EJ_THRESHOLDS["High"]:
        ej_tier = "High"
    elif avg_ej >= EJ_THRESHOLDS["Medium"]:
        ej_tier = "Medium"
    else:
        ej_tier = "Low"

    heat_vulnerable = len(trees) * RESIDENTS_PER_TREE_HIGH_EJ if ej_tier == "High" else 0

    return CoalitionSummary(
        tree_count=len(trees),
        canopy_sqft=round(total_canopy, 1),
        stormwater_gal_yr=round(total_stormwater, 0),
        co2_lbs_lifetime=round(total_co2, 0),
        cooling_usd_yr=round(total_cooling, 2),
        total_ecosystem_usd_yr=round(total_ecosystem, 2),
        ej_tier=ej_tier,
        heat_vulnerable_residents=heat_vulnerable,
        tree_ids=tree_ids,
    )
