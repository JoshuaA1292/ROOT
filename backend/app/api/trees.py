from fastapi import APIRouter, HTTPException, Query
from app.db.repositories.trees import get_tree_by_id, get_trees_in_bbox
from app.services.tree_ingestion import ingest_city_trees

router = APIRouter(prefix="/trees", tags=["trees"])


NYC_DEFAULT_BBOX = "-74.05,40.60,-73.85,40.80"


@router.get("")
async def list_trees(
    bbox: str = Query(None, description="lng1,lat1,lng2,lat2"),
):
    try:
        parts = [float(x) for x in (bbox or NYC_DEFAULT_BBOX).split(",")]
        if len(parts) != 4:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="bbox must be lng1,lat1,lng2,lat2")

    lng1, lat1, lng2, lat2 = parts
    # Scale limit with bbox size so zoomed-out views get enough trees
    bbox_area = (lng2 - lng1) * (lat2 - lat1)
    limit = min(3000, max(500, int(bbox_area * 8000)))
    trees = await get_trees_in_bbox(lng1, lat1, lng2, lat2, limit=limit)
    # Flatten for frontend
    return [
        {
            "id": str(t["_id"]),
            "species": t.get("species", {}).get("common", "Unknown"),
            "lng": t.get("location", {}).get("coordinates", [0, 0])[0],
            "lat": t.get("location", {}).get("coordinates", [0, 0])[1],
            "health": t.get("health", ""),
            "ecosystem_total_usd": t.get("ecosystem_value_usd_yr", {}).get("total_usd", 0),
            "diameter_in": t.get("diameter_in", 10),
        }
        for t in trees
    ]


@router.get("/{tree_id}")
async def get_tree(tree_id: str):
    tree = await get_tree_by_id(tree_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Tree not found")
    tree["id"] = str(tree.pop("_id"))
    return tree


@router.post("/ingest/{city}")
async def ingest_tree_inventory(city: str, body: dict | None = None):
    body = body or {}
    return await ingest_city_trees(
        city,
        records=body.get("records"),
        source_url=body.get("source_url"),
    )
