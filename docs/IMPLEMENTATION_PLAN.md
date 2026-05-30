# ROOT Implementation Plan

This plan tracks the gap between `ROOT_project_description.md` and the current implementation.

## Built

- FastAPI service with permit, tree, developer, precedent, briefing, and SSE endpoints.
- MongoDB repositories for the core collections.
- Coalition Agent for geospatial tree aggregation.
- Precedent Agent for vector-search RAG over prior permit cases.
- Developer Ledger Agent for survival-rate comparison against the 85% city target.
- Policy Agent for matching permit impacts to city canopy, heat, carbon, and replacement rules.
- Briefing Agent with Gemini fallback to a structured local placeholder.
- Next.js map flow with active permits, tree markers, coalition radius, progress stream, ledger, precedents, and editable comment draft.
- Steward review workflow with validated draft, edited, reviewed, exported, and submitted briefing states.
- Durable briefing job records with queued, running, completed, and failed states plus persisted event history.
- Replacement planting reconciliation service that rebuilds developer ledgers from planting and inspection records.
- MongoDB access-mode bridge and Agent Builder config for production MCP deployment with repository fallback for local tests.
- External-worker resume endpoint for queued or failed briefing jobs.
- NYC DOB permit ingestion service with normalization and upsert path.
- Parks planting-record ingestion service with reconciliation trigger.
- Resident workspace and agency export endpoints.
- Agent-pipeline observability metrics derived from persisted briefing job events.
- Cloud Scheduler deployment config for briefing resume, DOB permit ingestion, and Parks planting ingestion.
- Ingestion source configuration status endpoint.
- Workspace access enforcement via `X-ROOT-User-Email` identity header.
- Agency submission adapter stubs for NYC Parks and Community Board exports.
- Briefing quality scoring and failed/slow pipeline alert fields.
- Production env template entries for DOB, Parks, Portland, Seattle, auth mode, MCP, and agency adapter URLs.
- Multi-city tree inventory adapters and ingestion route for Portland and Seattle.
- Auth abstraction for dev header, IAP, Firebase-style email headers, and OAuth handoff.
- Optional live HTTP agency submission adapters with local stub fallback.
- Persisted briefing quality alerts and alert listing endpoint.
- Seed data and scripts for trees, permits, developers, precedents, indexes, and GCP setup.

## Not Yet Built

- Applied Cloud Scheduler jobs in a live GCP project. Deployment config exists but has not been run from this workspace.
- Live MongoDB MCP tool invocation from deployed Agent Engine. Production config is wired; local backend still uses typed repository fallbacks.
- Live replacement planting reconciliation against Parks inspection records. Normalization and ingestion are implemented; source URL must be configured.
- Production OAuth token validation. Auth-mode abstraction is implemented, but JWT verification is not.
- Confirmed live agency endpoint contracts. HTTP adapters are implemented, but endpoint URLs must be configured.
- Multi-city permit adapters beyond NYC. Portland and Seattle tree inventory adapters are implemented.

## Next Implementation Slices

1. Run `infra/cloudrun/deploy_scheduler.sh` with production `PROJECT_ID`, `SERVICE_URL`, and scheduler service account.
2. Configure `NYC_DOB_PERMIT_URL`, `PARKS_TREE_WORK_URL`, `PORTLAND_TREE_INVENTORY_URL`, and `SEATTLE_TREE_INVENTORY_URL` in Cloud Run secrets.
3. Add JWT verification for OAuth/Firebase tokens when not behind IAP.
4. Confirm agency submission schemas and configure `NYC_PARKS_SUBMISSION_URL` / `COMMUNITY_BOARD_SUBMISSION_URL`.
5. Add city-specific permit adapters for Portland and Seattle tree-work permit feeds.
