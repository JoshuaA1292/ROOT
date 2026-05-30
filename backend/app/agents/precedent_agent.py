"""
Precedent Agent: embeds the permit context and retrieves semantically similar
prior cases from the precedents collection via Atlas Vector Search.
"""
from app.services.embeddings import embed_text
from app.db.repositories.precedents import vector_search_precedents
from app.models.briefing import PrecedentRef


def _build_query_text(permit: dict, coalition_summary: dict) -> str:
    return (
        f"Tree removal permit in {permit.get('address', '')}. "
        f"Project type: {permit.get('project_type', '')}. "
        f"Stated reason: {permit.get('stated_reason', '')}. "
        f"Trees threatened: {coalition_summary.get('tree_count', 0)}. "
        f"Total ecosystem value: ${coalition_summary.get('total_ecosystem_usd_yr', 0):.0f}/yr. "
        f"EJ tier: {coalition_summary.get('ej_tier', 'Unknown')}."
    )


async def run(permit: dict, coalition_summary: dict, top_k: int = 5) -> list[PrecedentRef]:
    query_text = _build_query_text(permit, coalition_summary)
    embedding = embed_text(query_text)
    raw_results = await vector_search_precedents(embedding, top_k=top_k)

    return [
        PrecedentRef(
            id=str(r["_id"]),
            title=r.get("title", ""),
            outcome=r.get("outcome", ""),
            year=r.get("year", 0),
            similarity_score=round(r.get("score", 0.0), 4),
            arguments_used=r.get("arguments_used", []),
        )
        for r in raw_results
    ]
