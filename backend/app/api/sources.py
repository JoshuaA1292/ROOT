"""
Data sources / citations endpoint.
Returns the provenance records seeded from data_sources.json,
plus live collection counts from MongoDB so the frontend can show
"683,788 trees in database" etc.
"""
from fastapi import APIRouter
from app.db.client import get_db

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def get_data_sources():
    db = get_db()
    sources = await db.data_sources.find({}, {"_id": 0}).to_list(length=50)

    # Attach live counts
    counts = {
        "trees":           await db.trees.count_documents({}),
        "permits":         await db.permits.count_documents({}),
        "developers":      await db.developers.count_documents({}),
        "planting_records":await db.planting_records.count_documents({}),
        "briefings":       await db.briefings.count_documents({}),
    }
    return {"sources": sources, "live_counts": counts}
