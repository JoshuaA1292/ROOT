from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.client import get_db


async def get_tree_by_id(tree_id: str) -> dict | None:
    db = get_db()
    return await db.trees.find_one({"_id": tree_id})


async def get_trees_in_bbox(
    lng1: float, lat1: float, lng2: float, lat2: float, limit: int = 500
) -> list[dict]:
    db = get_db()
    cursor = db.trees.find(
        {
            "location": {
                "$geoWithin": {
                    "$box": [[lng1, lat1], [lng2, lat2]]
                }
            }
        },
        {"_id": 1, "species.common": 1, "location": 1, "health": 1,
         "ecosystem_value_usd_yr.total_usd": 1, "diameter_in": 1},
    ).limit(limit)
    return await cursor.to_list(length=limit)


async def get_trees_in_radius(
    lng: float, lat: float, radius_m: float
) -> list[dict]:
    db = get_db()
    cursor = db.trees.find(
        {
            "location": {
                "$geoWithin": {
                    "$centerSphere": [[lng, lat], radius_m / 6378137]  # radians
                }
            }
        }
    )
    return await cursor.to_list(length=200)


async def upsert_trees(trees: list[dict]) -> int:
    db = get_db()
    count = 0
    for tree in trees:
        await db.trees.update_one({"_id": tree["_id"]}, {"$set": tree}, upsert=True)
        count += 1
    return count
