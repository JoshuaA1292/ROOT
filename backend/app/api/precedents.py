from fastapi import APIRouter
from pydantic import BaseModel
from app.services.embeddings import embed_text
from app.db.repositories.precedents import vector_search_precedents

router = APIRouter(prefix="/precedents", tags=["precedents"])


class PrecedentSearchRequest(BaseModel):
    permit_context: str
    top_k: int = 5


@router.post("/search")
async def search_precedents(body: PrecedentSearchRequest):
    embedding = embed_text(body.permit_context)
    results = await vector_search_precedents(embedding, top_k=body.top_k)
    return [
        {
            "id": str(r["_id"]),
            "title": r.get("title", ""),
            "outcome": r.get("outcome", ""),
            "year": r.get("year", 0),
            "similarity_score": round(r.get("score", 0.0), 4),
            "arguments_used": r.get("arguments_used", []),
            "comment_excerpt": r.get("comment_text", "")[:300],
        }
        for r in results
    ]
