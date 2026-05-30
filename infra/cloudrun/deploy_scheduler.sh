#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"
: "${SERVICE_URL:?Set SERVICE_URL to the deployed ROOT API base URL}"
: "${SCHEDULER_SERVICE_ACCOUNT:?Set SCHEDULER_SERVICE_ACCOUNT}"

create_job() {
  local name="$1"
  local schedule="$2"
  local uri="$3"
  local description="$4"

  if gcloud scheduler jobs describe "$name" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "$name" \
      --project="$PROJECT_ID" \
      --location="$REGION" \
      --schedule="$schedule" \
      --time-zone="America/New_York" \
      --uri="$uri" \
      --http-method=POST \
      --oidc-service-account-email="$SCHEDULER_SERVICE_ACCOUNT" \
      --description="$description"
  else
    gcloud scheduler jobs create http "$name" \
      --project="$PROJECT_ID" \
      --location="$REGION" \
      --schedule="$schedule" \
      --time-zone="America/New_York" \
      --uri="$uri" \
      --http-method=POST \
      --oidc-service-account-email="$SCHEDULER_SERVICE_ACCOUNT" \
      --description="$description"
  fi
}

create_job "root-briefing-resume" "*/5 * * * *" \
  "${SERVICE_URL}/jobs/briefings/resume?limit=25" \
  "Resume queued or failed ROOT briefing jobs."

create_job "root-nyc-dob-permit-ingest" "*/15 * * * *" \
  "${SERVICE_URL}/permits/ingest" \
  "Ingest recent NYC DOB tree-work permit filings."

create_job "root-parks-planting-ingest" "0 */6 * * *" \
  "${SERVICE_URL}/developers/planting-records/ingest" \
  "Ingest Parks planting records and reconcile developer ledgers."
