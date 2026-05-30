"""Tests for precedent_agent — mocked embeddings and DB."""
import pytest
import app.agents.precedent_agent as precedent_agent
from app.agents.precedent_agent import run, _build_query_text


MOCK_PERMIT = {
    "address": "487 Atlantic Ave, Brooklyn",
    "project_type": "mixed_use_tower",
    "stated_reason": "Foundation excavation required.",
}

MOCK_COALITION = {
    "tree_count": 14,
    "total_ecosystem_usd_yr": 4200,
    "ej_tier": "High",
}

MOCK_RESULTS = [
    {
        "_id": "prec_0001",
        "title": "Brooklyn Heights Promenade — 2022",
        "outcome": "permit_modified",
        "year": 2022,
        "score": 0.91,
        "arguments_used": ["stormwater_load", "developer_history"],
    },
    {
        "_id": "prec_0002",
        "title": "Flatbush Avenue — 2021",
        "outcome": "denied",
        "year": 2021,
        "score": 0.84,
        "arguments_used": ["ecosystem_valuation"],
    },
]


def test_build_query_text_includes_key_fields():
    text = _build_query_text(MOCK_PERMIT, MOCK_COALITION)
    assert "Atlantic Ave" in text
    assert "mixed_use_tower" in text
    assert "14" in text
    assert "High" in text


@pytest.mark.asyncio
async def test_precedent_run_returns_refs(monkeypatch):
    async def async_search(embedding, top_k):
        return MOCK_RESULTS

    monkeypatch.setattr(precedent_agent, "embed_text", lambda text: [0.1] * 768)
    monkeypatch.setattr(precedent_agent, "vector_search_precedents", async_search)

    refs = await run(MOCK_PERMIT, MOCK_COALITION, top_k=2)

    assert len(refs) == 2
    assert refs[0].id == "prec_0001"
    assert refs[0].similarity_score == pytest.approx(0.91, abs=0.001)
    assert refs[1].outcome == "denied"
