from app.db.client import get_db, bson_clean


async def list_city_policies(jurisdiction: str = "NYC") -> list[dict]:
    db = get_db()
    cursor = db.city_policies.find({"jurisdiction": jurisdiction})
    docs = await cursor.to_list(length=100)
    return [bson_clean(d) for d in docs]
