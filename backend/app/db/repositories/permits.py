from app.db.client import get_db, bson_clean


async def get_permit_by_id(permit_id: str) -> dict | None:
    db = get_db()
    doc = await db.permits.find_one({"_id": permit_id})
    return bson_clean(doc) if doc else None


async def list_permits(status: str | None = None) -> list[dict]:
    db = get_db()
    query = {}
    if status:
        query["status"] = status
    cursor = db.permits.find(query).sort("comment_deadline", 1)
    docs = await cursor.to_list(length=100)
    return [bson_clean(d) for d in docs]


async def update_permit_threatened_trees(permit_id: str, tree_ids: list[str]) -> None:
    db = get_db()
    await db.permits.update_one(
        {"_id": permit_id},
        {"$set": {"threatened_tree_ids": tree_ids}}
    )


async def upsert_permits(permits: list[dict]) -> int:
    db = get_db()
    count = 0
    for permit in permits:
        permit_id = permit["_id"]
        await db.permits.update_one(
            {"_id": permit_id},
            {"$set": permit},
            upsert=True,
        )
        count += 1
    return count
