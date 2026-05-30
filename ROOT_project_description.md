# ROOT: The Urban Tree Intelligence Agent

> *Every threatened urban tree deserves a persistent identity, a living record, and a legal voice.*

---

## What ROOT Is

ROOT is an agentic civic intelligence system that gives urban trees a documented identity, tracks developer compliance with tree replacement promises, and automatically generates evidence-based public comment packages when a tree removal permit is filed.

It is not a chatbot. It is not a dashboard. It is a multi-agent pipeline that monitors, aggregates, retrieves precedent, and drafts — with a human making the final call.

ROOT solves a specific accountability asymmetry: developers promise to replace trees they remove, cities have no systematic way to check whether those promises were ever kept, and residents lack the evidence infrastructure to make meaningful public comments. ROOT builds that infrastructure.

---

## The Problem It Solves

When a developer files a permit to remove ten street trees and replace them with twelve saplings, no one is checking:

- Whether the last time this developer made that promise, those saplings actually survived
- Whether the cumulative loss from this permit contradicts the city's published canopy coverage targets
- What the actual dollar value of the ecosystem services being removed is
- Which residents in heat-vulnerable census tracts lose meaningful shade cover

ROOT monitors all of it — automatically, in real time, grounded in public data.

---

## Architecture Overview

ROOT is built on **MongoDB Atlas** as the primary data store, orchestrated by **Google Cloud Agent Builder**, powered by **Gemini**, and integrated with live public data APIs.

### The Tree Document

The atomic unit of ROOT is a MongoDB document — one per tree in the corpus. Each document contains:

- **Species and diameter** — sourced from city street tree census APIs (NYC, Portland, Seattle)
- **GPS coordinates** — enabling geospatial queries
- **Health status** — from city inventory systems
- **Ecosystem service valuations** — computed automatically via the USDA i-Tree Benefits API on ingest (carbon storage, stormwater interception, air pollution removal, cooling energy savings)
- **Heat vulnerability index** — from EPA EJScreen API, keyed to the tree's census tract
- **Permit event history** — all prior removals, replacements, and inspections affecting this tree or adjacent trees
- **Vector embedding** — of the full profile, enabling semantic similarity search via Atlas Vector Search

Documents are not static. Every new permit event, inspection record, or replacement planting appended to the corpus updates the tree's document and regenerates its embedding.

---

### The Developer Accountability Ledger

The centerpiece of ROOT. A persistent MongoDB collection — one document per developer entity, tracked by LLC name, parent company, and individual contractor license — containing:

- Total trees approved for removal across all permitted projects
- Total replacement trees promised across those permits
- Total replacement trees actually planted (cross-referenced against Parks Department planting records)
- Confirmed survival rate at 3-year and 5-year intervals where records exist

When a new permit triggers ROOT, the Ledger pulls that developer's **actual compliance history** — not their current application's promises. A developer with a 40% replacement survival rate is treated materially differently from one with 95%. This history currently exists nowhere in usable form. ROOT builds it from public permit records.

---

### The Agent Pipeline

ROOT uses Google Cloud Agent Builder to orchestrate four agents that fire sequentially when a permit is detected.

#### 1. Coalition Agent
Triggered by a new permit filing. Uses MongoDB Atlas geospatial queries to identify all trees within the permit's impact radius, then aggregates their ecosystem valuations into a single collective impact figure:

- Total canopy square footage threatened
- Combined annual stormwater interception (gallons)
- Combined lifetime carbon storage (lbs CO₂)
- Combined annual cooling energy savings ($)
- Number of residents in heat-vulnerable census tracts who lose meaningful shade cover

The coalition is not a metaphor. It is a multi-document aggregation pipeline that makes diffuse individual losses visible as a single coherent number.

#### 2. Precedent Agent
Uses Atlas Vector Search to retrieve semantically similar prior permit events — cases where a comparable species composition was threatened, in a similar neighborhood heat profile, by a similar developer class — and surfaces how those cases resolved and which arguments succeeded in public comment. This is the RAG layer, grounded in real civic history.

#### 3. Developer Ledger Agent
Pulls the filing developer's Accountability Ledger entry, computes their compliance rate against the city's published replacement survival target (typically 85%), and flags the delta as evidence for the comment record.

#### 4. Briefing Agent (Gemini)
Receives the coalition impact aggregate, the developer ledger entry, the precedent cases, and the current permit filing. Drafts a complete public comment package containing:

- A narrative section written for a non-expert resident
- A data appendix with ecosystem valuations and all calculations cited
- A policy contradiction section cross-referenced against the city's published climate goals and canopy targets (stored as reference documents in MongoDB)
- A list of specific questions the comment board should require the developer to answer on record

---

### Human Stewardship

ROOT does not file autonomously. The resident or advocate reviews the drafted package, edits as needed, and submits. ROOT is the research department. The human is the voice. This is a deliberate architectural choice: agentic systems operating in civic processes should be steward-supervised, not autonomous.

---

## Data Foundation

Every data source ROOT uses is publicly available today.

| Data Type | Source | Details |
|---|---|---|
| Tree inventory | NYC Open Data API | 683,000 trees with species, location, health, diameter — updated daily |
| Tree inventory | Portland Open Data | 252,180 street trees, re-inventoried 2024 |
| Tree inventory | Seattle Socrata API | Full city tree inventory at data.seattle.gov |
| Ecosystem valuation | USDA i-Tree Benefits API | Returns carbon, stormwater, air quality, cooling values by species and diameter |
| Heat vulnerability | EPA EJScreen API | Census tract-level heat and environmental justice indices |
| Permit filings | NYC DOB Open Data API | Real-time permit filings with impact radius and tree work categorization |
| Compliance records | NYC Parks Tree Work Permit records | Historical approvals, promised replacements, planting outcomes |

---

## Demo Flow

1. ROOT opens on a map showing the seeded corpus — 683,000 NYC trees as living documents.
2. A permit alert fires: a developer has filed to remove 14 trees on a Brooklyn block for a mixed-use development.
3. The Coalition Agent runs. Output: 4,200 sq ft canopy loss. 112,000 gallons annual stormwater interception lost. $8,400/year cooling value lost. 340 residents in a high heat-vulnerability census tract lose meaningful shade.
4. The Ledger Agent pulls the developer's history: 3 prior Brooklyn permits. 31 replacements promised. 24 planted. 14 confirmed alive at 3 years. Survival rate: 45%. City target: 85%.
5. The Precedent Agent surfaces two similar cases from other boroughs where the replacement survival argument was used successfully in public comment.
6. Gemini drafts the comment package. Opening line: *"This application proposes the removal of 14 trees whose combined ecosystem services are valued at $312,000 in present-value terms. The applicant's prior compliance record across 3 approved permits shows a 45% survival rate on promised replacements, compared to the city's 85% target..."*
7. The resident reviews, edits two sentences, clicks Submit.

**Total time from permit alert to draft: under 90 seconds.**

---

## Why MongoDB Atlas

ROOT's data model is inherently document-shaped and heterogeneous. A tree's record is not a fixed schema — it is a living object that grows over time with species data, health assessments, ecosystem valuations, permit history, and replacement outcomes. That growth doesn't fit cleanly in a relational model.

Atlas specifically enables:

- **Document model** — heterogeneous, evolving tree and developer records without schema migration overhead
- **Geospatial queries** — finding all trees within a permit's impact radius in a single query
- **Atlas Vector Search** — semantic retrieval of precedent permit cases by profile similarity
- **MongoDB MCP server** — Gemini reads and writes to the living corpus without a custom API layer

ROOT demonstrates Atlas as civic infrastructure: a living document store for the physical world.

---

## Scale Context

There are approximately 36 million street trees in U.S. cities, governed by roughly 200,000 tree work permit applications annually. ROOT's architecture is city-agnostic — any municipality with a public tree inventory and permit API can be ingested into the corpus. NYC is the seed. The model is replicable.

---

## Judging Criteria Alignment

| Criterion | ROOT's Position |
|---|---|
| **Technological Implementation** | MongoDB Atlas (document store, geospatial, vector search, MCP), Google Cloud Agent Builder (multi-agent orchestration), Gemini (briefing generation), four live public APIs |
| **Design** | Steward-supervised agentic pipeline; human approves before any civic action is taken |
| **Potential Impact** | Directly addresses canopy loss accountability gap across 36M U.S. street trees and 200K annual permits |
| **Quality of Idea** | Developer Accountability Ledger is an original, defensible data product that does not currently exist in usable form anywhere |

---

*ROOT was conceived for the Google Cloud Rapid Agent Hackathon, MongoDB Partner Track.*
