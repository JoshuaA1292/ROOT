# ROOT Architecture

## System Overview

ROOT is a multi-agent pipeline that processes a tree removal permit and produces a human-reviewable public comment draft. The system is designed around four constraints:

1. **Demo reliability** — all data is pre-computed; no runtime calls to i-Tree or EJScreen during the demo
2. **Human in the loop** — ROOT drafts, humans submit; `POST /briefings/{id}/submit` marks status only
3. **Real-time feedback** — SSE streams each agent step as it completes, so users see progress within seconds
4. **Dual-mode operation** — full ADK `LlmAgent` when `GOOGLE_CLOUD_PROJECT` is set; direct deterministic Python pipeline otherwise (local dev with `GOOGLE_AI_STUDIO_KEY`)

---

## Request Lifecycle

```
Browser
  │
  │  POST /briefings {permit_id}
  ▼
FastAPI (Cloud Run)
  │
  ├── create_briefing() → MongoDB briefings collection → returns briefing_id
  │
  ├── asyncio.create_task(_run(permit_id, briefing_id))   ← non-blocking
  │
  └── returns {briefing_id, status: "running"}            ← immediately

Browser                FastAPI background task
  │                        │
  │  GET /stream/           │
  │  briefings/{id}  ◄──── │ asyncio.Queue events pushed as each step completes
  │  (SSE)                  │
  │                         ├── permit_loaded
  │                         ├── coalition_start → coalition_complete
  │                         ├── developer_loaded
  │                         ├── precedent_start → precedent_complete
  │                         ├── briefing_start → briefing_complete
  │                         └── done → None sentinel (closes SSE)
```

---

## Agent Pipeline

### Coalition Agent (`app/agents/coalition_agent.py`)

**Input:** permit document (center coordinates, removal_radius_m)

**Steps:**
1. `$geoWithin $centerSphere` query against `trees` collection (via MongoDB MCP)
2. Aggregate species, diameter, health across all matched trees
3. Sum pre-computed `ecosystem_value_usd_yr` fields (stormwater, CO₂, cooling, air quality)
4. Look up `ej_score.heat_vuln_pct` for the permit's census tract
5. Classify EJ tier: High (≥70th pct), Medium (40-70th pct), Low (<40th pct)

**Output:** `CoalitionSummary` Pydantic model

### Precedent Agent (`app/agents/precedent_agent.py`)

**Input:** permit context string (address, project_type, coalition summary, EJ tier)

**Steps:**
1. Embed context string using `gemini-embedding-001` with `output_dimensionality=768`
2. Atlas Vector Search: cosine similarity over `precedents.embedding`, top-5
3. Filter to score ≥ 0.75

**Output:** list of `PrecedentRef` models with `similarity_score` and `arguments_used`

### Briefing Agent (`app/agents/briefing_agent.py`)

**Input:** permit + coalition + developer + precedents + policy references

**Steps:**
1. Build structured prompt with all payloads (see `prompts/briefing_system.md`)
2. Call `google.genai` client with `models/gemini-2.5-flash` (API key mode or Vertex AI mode)
3. Parse response text + extract `Citations & Data Sources` appendix

**Output:** `(draft_comment: str, citations: list[str])`

**Fallback:** If Gemini raises (no credentials or rate limit), `_placeholder_comment()` generates a structured PLACEHOLDER draft with all real calculated values. The UI always renders something usable — the placeholder is clearly labelled so the resident knows it needs Gemini to produce the final version.

---

## Data Model

### `trees`
```json
{
  "_id": "tree_bk_001",
  "nyc_tree_id": 180683,
  "species": {"common": "London planetree", "latin": "Platanus x acerifolia"},
  "diameter_in": 21.5,
  "health": "Good",
  "location": {"type": "Point", "coordinates": [-73.9848, 40.6859]},
  "ecosystem_value_usd_yr": {
    "stormwater_gal": 1820, "co2_lbs": 312, "cooling_kwh": 45,
    "total_usd": 380
  },
  "ej_score": {"heat_vuln_pct": 72, "tract_score": 0.81}
}
```

### `permits`
```json
{
  "_id": "permit_2026_0184",
  "developer_id": "dev_atlas_holdings",
  "center": {"type": "Point", "coordinates": [-73.9845, 40.6862]},
  "removal_radius_m": 80,
  "comment_deadline": "2026-06-25",
  "status": "open_for_comment"
}
```

### `developers`
```json
{
  "_id": "dev_atlas_holdings",
  "name": "Atlas Holdings LLC",
  "compliance_rate": 0.45,
  "violations": [{"permit_id": "p1", "type": "missing_replacement", "count": 3, "year": 2022}]
}
```

### `precedents`
```json
{
  "_id": "prec_0001",
  "title": "Brooklyn Heights Mixed-Use 2022",
  "outcome": "permit_modified",
  "arguments_used": ["stormwater_load", "ej_equity"],
  "embedding": [0.021, -0.043, ...]
}
```

---

## MongoDB MCP Integration

`mcp/mcp.config.json` configures `@mongodb-js/mongodb-mcp-server` to connect to Atlas. When running with `GOOGLE_CLOUD_PROJECT` set, Agent Builder invokes MongoDB operations via MCP rather than direct Motor calls. The MCP server exposes `find`, `aggregate`, `insertOne`, `updateOne`, and `vectorSearch` as tool schemas that Agent Builder's LLM can call.

In local dev (direct mode), Motor is used directly via the repository layer.

---

## SSE Queue Registry

```python
_queues: dict[str, asyncio.Queue] = {}
```

The orchestrator maintains a dict of asyncio Queues keyed by briefing_id. The background pipeline task pushes events to `_queues[briefing_id]`; the SSE endpoint subscribes by calling `events_for_briefing(briefing_id)` which reads from the same queue. A `None` sentinel signals end-of-stream. Queues are never explicitly cleaned up (bounded by the number of active briefings).

---

## Deployment

```
GitHub push to main
    │
    ├── .github/workflows/deploy.yml
    │     ├── gcloud builds submit ./backend → gcr.io/$PROJECT/root-backend
    │     ├── gcloud run deploy root-backend (min-instances=1, Secret Manager mounts)
    │     └── vercel deploy --prod (reads NEXT_PUBLIC_API_URL from Vercel env)
    │
    └── Vercel automatic preview deploys on PRs
```

**Secrets in Cloud Run** (never in source):
- `MONGODB_URI` — mounted from Secret Manager `mongodb-uri`
- `GOOGLE_APPLICATION_CREDENTIALS` — implicit via Workload Identity on service account
- `CORS_ORIGINS` — set as plain env var (non-sensitive)

**Secrets in Vercel**:
- `NEXT_PUBLIC_API_URL` — Cloud Run service URL (set post-deploy)

Note: the map uses OpenStreetMap tiles via Leaflet — no Mapbox token required.
