from app.db.client import get_db, bson_clean


async def get_developer_by_id(developer_id: str) -> dict | None:
    db = get_db()
    doc = await db.developers.find_one({"_id": developer_id})
    return bson_clean(doc) if doc else None


async def list_developers(limit: int = 100) -> list[dict]:
    db = get_db()
    cursor = db.developers.find({}).sort("compliance_rate", 1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [bson_clean(d) for d in docs]


async def upsert_developer_ledger(developer_id: str, update_data: dict) -> None:
    db = get_db()
    await db.developers.update_one(
        {"_id": developer_id},
        {"$set": update_data, "$setOnInsert": {"_id": developer_id, "linked_entities": []}},
        upsert=True,
    )
