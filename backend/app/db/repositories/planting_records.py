from app.db.client import get_db


async def list_planting_records(developer_id: str | None = None) -> list[dict]:
    db = get_db()
    query = {"developer_id": developer_id} if developer_id else {}
    cursor = db.planting_records.find(query)
    return await cursor.to_list(length=1000)


async def upsert_planting_records(records: list[dict]) -> int:
    db = get_db()
    count = 0
    for record in records:
        record_id = record["_id"]
        await db.planting_records.update_one(
            {"_id": record_id},
            {"$set": record},
            upsert=True,
        )
        count += 1
    return count
