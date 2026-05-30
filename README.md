# ROOT — Urban Tree Intelligence Agent

> Every threatened urban tree gets a persistent identity, a living record, and a legal voice.
> ROOT holds developers accountable for what they actually plant versus what they promise.

**Submission for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com) · MongoDB Partner Track**

[![Backend CI](https://github.com/your-repo/root/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/your-repo/root/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/your-repo/root/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/your-repo/root/actions/workflows/frontend-ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

---

## The Problem

When a developer files a permit to remove 10 street trees and replace them with 12 saplings, the city has no systematic way to check whether those saplings survived last time. ROOT solves that asymmetry.

There are ~36 million street trees in U.S. cities, covered by approximately 200,000 permit applications annually. Individual losses are diffuse and invisible. Collectively, they determine whether cities hit their 30% canopy targets by 2035.

---

## How It Works

1. A developer files a permit to remove street trees
2. ROOT's **Coalition Agent** identifies every threatened tree within the permit radius, aggregates their combined ecosystem value (stormwater, carbon, cooling), and scores environmental justice exposure
3. ROOT's **Precedent Agent** uses Atlas Vector Search to find prior permit cases where similar arguments succeeded in public comment
4. ROOT's **Developer Ledger Agent** pulls the applicant's real replacement survival rate across all prior permits from the Developer Accountability Ledger
5. ROOT's **Briefing Agent** (Gemini 2.5 Flash) synthesizes everything into a legally-grounded public comment draft
6. A human resident reviews, edits, and submits — **ROOT does not file autonomously** (steward-supervised agentic action)

**Total time from permit alert to draft: under 90 seconds.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Browser                                  │
│  Next.js 14 · Leaflet + OpenStreetMap · SSE progress stream             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  HTTPS
┌────────────────────────────▼────────────────────────────────────────────┐
│               Google Cloud Run  (FastAPI / Python 3.11)                 │
│                                                                         │
│  POST /briefings  ──►  Orchestrator                                     │
│                            │                                            │
│        ┌───────────────────┼───────────────────┐                        │
│        │                   │                   │                        │
│  ┌─────▼──────┐   ┌────────▼───────┐   ┌──────▼──────┐                 │
│  │ Coalition  │   │  Developer     │   │  Briefing   │                 │
│  │   Agent   │   │  Ledger Agent  │   │   Agent     │                 │
│  │ $geoWithin │   │  Compliance   │   │ Gemini 2.5  │                 │
│  └─────┬──────┘   └────────┬───────┘   └──────┬──────┘                 │
│        │                   │                   │                        │
│  ┌─────▼──────┐   ┌────────▼───────┐           │                        │
│  │  Precedent │   │  Policy Agent  │           │                        │
│  │   Agent    │   │  City targets  │           │                        │
│  │ Vector RAG │   └────────────────┘           │                        │
│  └────────────┘                                │                        │
│        └────────────────────────────────────────┘                       │
│                            │  Motor (direct) or MCP                     │
└────────────────────────────┼────────────────────────────────────────────┘
                             │  TLS
┌────────────────────────────▼────────────────────────────────────────────┐
│                       MongoDB Atlas                                     │
│  trees · permits · developers · precedents · briefings · city_policies  │
│  2dsphere index · Atlas Vector Search (768-dim cosine)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Dual-mode operation:** When `GOOGLE_CLOUD_PROJECT` is set, the orchestrator uses the Google ADK `LlmAgent` with Vertex AI (Gemini orchestrates tool calls). Without it, the orchestrator runs a direct deterministic Python pipeline — same four agents, no Gemini orchestration overhead. For local development, only `GOOGLE_AI_STUDIO_KEY` is needed.

---

## Technology Stack

### Google Cloud — Orchestration Spine

| Component | Role |
|---|---|
| **Google ADK 2.1** | `LlmAgent` + `InMemoryRunner` + tool callbacks for SSE event streaming (ADK mode) |
| **Gemini 2.5 Flash** | Reasoning and comment synthesis in the Briefing Agent via `google.genai` unified SDK |
| **`gemini-embedding-001`** | 768-dim embeddings (output_dimensionality=768) for Atlas Vector Search RAG |
| **Cloud Run** | Serverless backend (min-instances=1 for demo reliability) |
| **Secret Manager** | Credential management in production; `MONGODB_URI` never in code |

### MongoDB — Partner Track

| Component | Role |
|---|---|
| **MongoDB Atlas** | Document store for heterogeneous tree records that accumulate over time |
| **Atlas Geospatial** | `$geoWithin $centerSphere` finds all trees inside a permit's removal radius |
| **Atlas Vector Search** | Cosine similarity over 768-dim embeddings on `precedents.embedding` for RAG |
| **MongoDB MCP Server** | `@mongodb-js/mongodb-mcp-server` — Agent Builder calls MongoDB via MCP in production; Motor repository layer for local dev |

### Why MongoDB (not SQL)

Each tree's document is heterogeneous: species and diameter from the Street Tree Census, ecosystem valuations from USDA i-Tree, EJ scores from EPA EJScreen, and permit outcomes accumulate over years. A relational schema would require 6+ joins per tree lookup. MongoDB's document model handles this naturally, and Atlas Vector Search is co-located with operational data — no separate vector database.

---

## Judging Criteria

| Criterion | ROOT's answer |
|---|---|
| **Technological Implementation** | ADK LlmAgent (direct mode) or Agent Builder (production); Gemini 2.5 Flash synthesis; Atlas Vector Search RAG; MongoDB MCP for all DB operations in production; four coordinated agents running in under 90 seconds |
| **Design** | Map-first UI with real-time 4-step progress stepper, developer ledger visualization, coalition radius overlay on map, editable comment editor, human-in-the-loop submit flow; SSE streams each tool call as it completes |
| **Potential Impact** | 36M U.S. street trees, ~200K permits/year; ROOT makes diffuse individual tree losses visible as collective civic evidence; directly supports cities' 30% canopy targets by 2035 |
| **Quality of Idea** | Developer Accountability Ledger is novel — a developer's real replacement survival rate currently exists nowhere in usable form; ROOT builds it from public permit records and makes it actionable in every public comment |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- MongoDB Atlas account (free M0 cluster works; requires 2dsphere + Vector Search indexes)
- Google AI Studio key (free at [aistudio.google.com](https://aistudio.google.com)) **or** GCP service account with Vertex AI

### 1. Clone & configure

```bash
git clone https://github.com/your-repo/root
cd root
cp .env.example .env
# Required: MONGODB_URI, GOOGLE_AI_STUDIO_KEY
# See .env.example for all variables
```

### 2. Seed data

```bash
cd backend
python -m pip install -e ".[dev]"

cd ../data
python scripts/01_fetch_nyc_trees.py      # fetch ~1000 NYC trees from Open Data API
python scripts/02_enrich_itree.py         # compute ecosystem valuations
python scripts/03_enrich_ejscreen.py      # add EPA EJScreen heat vulnerability scores
python scripts/04_seed_mongo.py           # load everything into Atlas
python scripts/05_embed_precedents.py     # embed 10 precedent cases (needs AI key)
python scripts/06_create_indexes.py       # create 2dsphere + vector indexes
```

**Atlas Vector Search index** (create in Atlas UI after step 06):
- Collection: `precedents`, Index name: `precedents_vector_index`
- Field: `embedding`, dimensions: `768`, similarity: `cosine`

### 3. Run backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 5. Deploy (optional)

```bash
# Backend → Cloud Run
bash infra/cloudrun/deploy.sh

# Frontend → Vercel
vercel --prod
# Set: NEXT_PUBLIC_API_URL=<Cloud Run service URL>
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MONGODB_URI` | Yes | Atlas connection string |
| `MONGODB_DB` | No | Database name (default: `root_trees`) |
| `GOOGLE_AI_STUDIO_KEY` | For local dev | Free key from aistudio.google.com |
| `GOOGLE_CLOUD_PROJECT` | For production | Enables ADK + Vertex AI pipeline |
| `GOOGLE_APPLICATION_CREDENTIALS` | For production | Path to service account JSON |
| `GEMINI_MODEL` | No | Gemini model (default: `models/gemini-2.5-flash`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `NYC_DOB_PERMIT_URL` | For live ingestion | NYC DOB NOW permits Socrata endpoint |
| `PARKS_TREE_WORK_URL` | For live ingestion | NYC Parks tree work records |
| `PORTLAND_TREE_INVENTORY_URL` | For live ingestion | Portland ArcGIS tree inventory |
| `SEATTLE_TREE_INVENTORY_URL` | For live ingestion | Seattle Socrata tree inventory |

---

## Demo Flow

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for the full step-by-step demo walkthrough.

Quick version:

1. Open `/map` — 1,019 Brooklyn trees render as green dots (7,500 available in the extended corpus); active permits show in the sidebar
2. Click **487 Atlantic Ave, Brooklyn** in the sidebar
3. The coalition radius circle appears on the map; threatened trees turn orange
4. Click **"Analyze this permit"**
5. Watch the progress bar: Coalition → Developer → Precedents → Policy → Gemini
6. Agent steps stream live: 24 trees threatened, $775/yr ecosystem value, 45% developer compliance rate
7. Gemini draft loads on the right — a complete, legally-grounded public comment
8. Edit any sentence → click **Submit** → status flips to `submitted`

---

## Tests

```bash
cd backend
pytest tests/ -v
# 53 tests covering: API health, coalition agent, precedent agent, developer ledger,
# orchestrator pipeline, ADK tools, briefing jobs, reconciliation, observability
```

---

## Project Structure

```
ROOT/
├── backend/
│   ├── app/agents/         orchestrator, coalition, precedent, developer_ledger,
│   │                       policy, briefing, adk_agent
│   ├── app/api/            REST endpoints + SSE stream
│   ├── app/db/             Motor client + typed repository layer
│   ├── app/services/       ingestion, embeddings, exports, reconciliation
│   └── tests/              53 pytest tests (all mocked, no GCP required)
├── frontend/
│   └── src/
│       ├── app/            landing page, map page, permit detail page
│       └── components/     TreeMap, AgentStream, BriefingEditor,
│                           CoalitionSummary, DeveloperLedger, PrecedentList
├── data/
│   ├── seed/               Pre-built JSON (1,019 trees, 15 permits, 11 developers,
│   │                       30 precedents, city policies)
│   └── scripts/            Fetch → enrich → seed → embed pipeline (01–07)
├── mcp/                    MongoDB MCP server config (production path)
├── infra/                  Cloud Run + deploy scripts + Vercel config
└── docs/
    ├── ARCHITECTURE.md     Request lifecycle + agent pipeline detail
    └── DEMO_SCRIPT.md      Step-by-step demo walkthrough
```

---

*Synthetic demo data · ROOT is research assistance only · You are the voice*
