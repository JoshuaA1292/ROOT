import math
from app.db.client import get_db, bson_clean


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def vector_search_precedents(
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    db = get_db()

    # Try Atlas Vector Search first
    pipeline = [
        {
            "$vectorSearch": {
                "index": "precedents_vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 20,
                "limit": top_k,
            }
        },
        {
            "$project": {
                "embedding": 0,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    try:
        cursor = db.precedents.aggregate(pipeline)
        docs = await cursor.to_list(length=top_k)
        if docs:
            return [bson_clean(d) for d in docs]
    except Exception:
        pass

    # Fallback: load all precedents and compute cosine similarity in Python
    all_docs = await db.precedents.find({}).to_list(length=200)
    scored = []
    for doc in all_docs:
        emb = doc.get("embedding", [])
        if len(emb) == len(query_embedding):
            score = _cosine_similarity(query_embedding, emb)
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:top_k]:
        cleaned = bson_clean({k: v for k, v in doc.items() if k != "embedding"})
        cleaned["score"] = score
        results.append(cleaned)
    return results


async def get_precedent_by_id(precedent_id: str) -> dict | None:
    db = get_db()
    return await db.precedents.find_one({"_id": precedent_id}, {"embedding": 0})
