from app.db.client import get_db, bson_clean


async def vector_search_precedents(
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    db = get_db()
    pipeline = [
        {
            "$vectorSearch": {
                "index": "precedents_vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 10,
                "limit": top_k,
            }
        },
        {
            "$project": {
                "embedding": 0,  # exclude large field from response
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    cursor = db.precedents.aggregate(pipeline)
    docs = await cursor.to_list(length=top_k)
    return [bson_clean(d) for d in docs]


async def get_precedent_by_id(precedent_id: str) -> dict | None:
    db = get_db()
    return await db.precedents.find_one({"_id": precedent_id}, {"embedding": 0})
