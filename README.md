# ROOT: Urban Tree Intelligence

ROOT is a civic tool that helps residents respond to street tree removal permits. It finds every threatened tree near a proposed removal, pulls the developer's real replacement survival history, and drafts a legally-grounded public comment for a resident to review and file.

**Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com) and MongoDB Partner Track**

---

## The problem

When a developer files a permit to remove 10 trees and promises to plant 12 replacements, there's no easy way to check if they kept that promise last time. That gap exists across every city. ROOT closes it.

There are roughly 36 million street trees in U.S. cities and around 200,000 tree removal permits filed each year. Each loss is small. Collectively they determine whether cities hit their 30% canopy targets by 2035. Nobody is tracking this at the permit level.

---

## How it works

1. A developer files a permit to remove street trees
2. The **Coalition Agent** finds every threatened tree within the removal radius and calculates their combined ecosystem value: stormwater interception, carbon storage, cooling, air quality
3. The **Precedent Agent** uses Atlas Vector Search to find prior cases where similar arguments got enforceable conditions added to a permit
4. The **Developer Ledger Agent** looks up the applicant's actual replacement survival rate across all prior permits
5. The **Briefing Agent** (Gemini 2.5 Flash) puts it all together into a draft public comment
6. A resident reads it, edits it, and decides whether to file. ROOT does not submit anything on its own.

From permit to draft in under 90 seconds.

---

## Architecture

```
User Browser (Next.js 14, Leaflet, SSE stream)
        |
        | HTTPS
        v
FastAPI / Python 3.11 (Render)
        |
   Orchestrator
        |
   +-----------+----------+-----------+
   |           |          |           |
Coalition  Developer  Precedent   Policy
 Agent      Ledger     Agent       Agent
$geoWithin  Compliance Vector RAG  City rules
        |
        v
Briefing Agent (Gemini 2.5 Flash)
        |
        | Motor / MCP
        v
MongoDB Atlas
trees, permits, developers, precedents, briefings, city_policies
2dsphere index + Atlas Vector Search (768-dim cosine)
```

Two modes: when `GOOGLE_CLOUD_PROJECT` is set, the orchestrator uses the Google ADK `LlmAgent` with Vertex AI (Gemini drives the tool calls). Without it, the orchestrator runs a direct deterministic Python pipeline with the same four agents. Local dev only needs a free `GOOGLE_AI_STUDIO_KEY`.

---

## Technology

### Google Cloud

| Component | What it does |
|---|---|
| Google ADK 2.1 | `LlmAgent` with `InMemoryRunner` and tool callbacks for live SSE streaming |
| Gemini 2.5 Flash | Reasoning and comment synthesis in the Briefing Agent |
| `gemini-embedding-001` | 768-dim embeddings for Atlas Vector Search RAG |
| Cloud Run | Serverless backend option (min-instances=1 for demo) |
| Secret Manager | Credential management in production |

### MongoDB

| Component | What it does |
|---|---|
| MongoDB Atlas | Document store for tree records that accumulate over time |
| Atlas Geospatial | `$geoWithin $centerSphere` finds all trees inside a removal radius |
| Atlas Vector Search | Cosine similarity over 768-dim embeddings on `precedents.embedding` |
| MongoDB MCP Server | `@mongodb-js/mongodb-mcp-server` for agent tool calls in production |

### Why not SQL

Each tree record is heterogeneous: species and diameter from the Street Tree Census, ecosystem valuations from USDA i-Tree, EJ scores from EPA EJScreen, and permit outcomes that accumulate over years. A relational schema would need 6+ joins per lookup. MongoDB handles it naturally, and Atlas Vector Search runs in the same cluster so there is no separate vector database to manage.

---

## Hackathon criteria

| Criterion | ROOT's approach |
|---|---|
| Technological Implementation | ADK LlmAgent + Gemini 2.5 Flash synthesis + Atlas Vector Search RAG + MongoDB MCP for all DB operations in production; four coordinated agents in under 90 seconds |
| Design | Map-first UI with real-time progress stream, developer ledger view, coalition radius overlay, editable comment editor, human-in-the-loop submit flow |
| Potential Impact | 36M U.S. street trees, ~200K permits/year; makes diffuse individual losses visible as collective civic evidence |
| Quality of Idea | The Developer Accountability Ledger is novel. A developer's real replacement survival rate does not exist in usable public form anywhere. ROOT builds it from permit records and puts it into every comment draft. |

---

## Setup

### What you need
- Python 3.11+
- Node.js 20+
- MongoDB Atlas account (free M0 cluster; requires 2dsphere and Vector Search indexes)
- Google AI Studio key (free at [aistudio.google.com](https://aistudio.google.com)) or a GCP service account with Vertex AI

### 1. Clone and configure

```bash
git clone https://github.com/JoshuaA1292/ROOT
cd ROOT
cp backend/.env.example backend/.env
# Fill in MONGODB_URI and GOOGLE_AI_STUDIO_KEY at minimum
```

### 2. Seed the database

```bash
cd backend
pip install -e ".[dev]"

cd ../data
python scripts/01_fetch_nyc_trees.py      # ~1000 NYC trees from Open Data
python scripts/02_enrich_itree.py         # ecosystem valuations
python scripts/03_enrich_ejscreen.py      # EPA EJScreen heat vulnerability
python scripts/04_seed_mongo.py           # load into Atlas
python scripts/05_embed_precedents.py     # embed precedent cases (needs AI key)
python scripts/06_create_indexes.py       # 2dsphere + vector indexes
```

Atlas Vector Search index to create in the Atlas UI after step 6:
- Collection: `precedents`, Index: `precedents_vector_index`
- Field: `embedding`, dimensions: `768`, similarity: `cosine`

### 3. Run backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# Check: http://localhost:8000/health
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:3000
```

### 5. Deploy

```bash
# Backend: Render (docker, see render.yaml)
# Frontend: Vercel
vercel --prod
# Set NEXT_PUBLIC_API_URL to your Render backend URL
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `MONGODB_URI` | Yes | Atlas connection string |
| `MONGODB_DB` | No | Database name (default: `root_trees`) |
| `GOOGLE_AI_STUDIO_KEY` | For local dev | Free from aistudio.google.com |
| `GOOGLE_CLOUD_PROJECT` | For production | Enables ADK + Vertex AI pipeline |
| `GOOGLE_APPLICATION_CREDENTIALS` | For production | Path to service account JSON |
| `GEMINI_MODEL` | No | Default: `models/gemini-2.5-flash` |
| `MAILJET_API_KEY` | For email | Guardian notification emails |
| `MAILJET_SECRET_KEY` | For email | Guardian notification emails |
| `NOTIFICATION_EMAIL` | For email | Where guardian alerts are copied |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |

---

## Demo

Full walkthrough: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)

Short version:

1. Open `/map` and pick any amber permit marker in the sidebar
2. The coalition radius appears on the map; threatened trees turn orange
3. Click "Analyze this permit"
4. Watch the live progress: Coalition, Developer, Precedents, Policy, Gemini
5. The draft loads on the right. Read it, edit it, and decide if you want to file it.

---

## Tests

```bash
cd backend
pytest tests/ -v
# Covers: API health, coalition agent, precedent agent, developer ledger,
# orchestrator pipeline, ADK tools, briefing jobs, reconciliation
```

---

## Project structure

```
ROOT/
├── backend/
│   ├── app/agents/      orchestrator, coalition, precedent, developer_ledger, policy, briefing, adk_agent
│   ├── app/api/         REST endpoints and SSE stream
│   ├── app/db/          Motor client and typed repository layer
│   └── app/services/    ingestion, embeddings, notifications, guardian scheduler
├── frontend/
│   └── src/
│       ├── app/         landing page, map page, permit detail
│       └── components/  TreeMap, AgentStream, BriefingEditor, CoalitionSummary, DeveloperLedger
├── data/
│   ├── seed/            Pre-built JSON (trees, permits, developers, precedents, policies)
│   └── scripts/         Fetch, enrich, seed, embed pipeline (01-07)
└── docs/
    ├── ARCHITECTURE.md  Request lifecycle and agent pipeline detail
    └── DEMO_SCRIPT.md   Step-by-step demo walkthrough
```

---

*Synthetic demo data. ROOT is a research and drafting tool. You review and decide what gets filed.*
