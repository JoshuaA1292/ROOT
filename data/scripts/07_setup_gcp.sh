#!/usr/bin/env bash
# ROOT — Google Cloud Project Setup Script
# Run this once to enable all required APIs and create the service account.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated: gcloud auth login
#   - Project ID set: gcloud config set project <YOUR_PROJECT_ID>
#
# Usage: bash data/scripts/07_setup_gcp.sh

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: No GCP project set. Run: gcloud config set project <YOUR_PROJECT_ID>"
  exit 1
fi

echo "==> Setting up ROOT on project: ${PROJECT_ID}"

# ── Enable required APIs ──────────────────────────────────────────────────────
echo ""
echo "1. Enabling required APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  generativelanguage.googleapis.com \
  --project="${PROJECT_ID}"
echo "   APIs enabled."

# ── Service account ───────────────────────────────────────────────────────────
SA_NAME="root-backend-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "2. Creating service account: ${SA_EMAIL}"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="ROOT Backend Service Account" \
    --project="${PROJECT_ID}"
fi

# Grant required roles
for ROLE in \
  "roles/aiplatform.user" \
  "roles/secretmanager.secretAccessor" \
  "roles/run.invoker"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --quiet
done
echo "   Service account created and roles granted."

# ── Store MongoDB URI in Secret Manager ───────────────────────────────────────
echo ""
echo "3. Setting up Secret Manager..."
if [ -f ".env" ]; then
  MONGODB_URI=$(grep '^MONGODB_URI=' .env | cut -d= -f2-)
  if [ -n "$MONGODB_URI" ]; then
    # Create or update the secret
    if gcloud secrets describe "mongodb-uri" --project="${PROJECT_ID}" &>/dev/null; then
      echo "${MONGODB_URI}" | gcloud secrets versions add "mongodb-uri" --data-file=- --project="${PROJECT_ID}"
      echo "   Updated existing 'mongodb-uri' secret."
    else
      echo "${MONGODB_URI}" | gcloud secrets create "mongodb-uri" --data-file=- --project="${PROJECT_ID}"
      echo "   Created 'mongodb-uri' secret."
    fi
  else
    echo "   WARNING: MONGODB_URI not found in .env — create the secret manually."
  fi
else
  echo "   WARNING: .env not found — create Secret Manager secret 'mongodb-uri' manually."
fi

# ── Create local service account key (dev only) ───────────────────────────────
KEY_FILE="./gcp-service-account.json"
if [ ! -f "$KEY_FILE" ]; then
  echo ""
  echo "4. Creating local service account key (dev only)..."
  gcloud iam service-accounts keys create "${KEY_FILE}" \
    --iam-account="${SA_EMAIL}" \
    --project="${PROJECT_ID}"
  echo "   Key saved to ${KEY_FILE} — add to .env: GOOGLE_APPLICATION_CREDENTIALS=${KEY_FILE}"
  echo "   WARNING: Never commit ${KEY_FILE} to git."
else
  echo ""
  echo "4. Service account key already exists at ${KEY_FILE}."
fi

echo ""
echo "==> Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add to your .env:"
echo "     GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
echo "     GOOGLE_APPLICATION_CREDENTIALS=./gcp-service-account.json"
echo "  2. Run the seed pipeline:"
echo "     python data/scripts/04_seed_mongo.py"
echo "     python data/scripts/05_embed_precedents.py"
echo "  3. Create Atlas Vector Search index (see README)"
echo "  4. Start backend: cd backend && uvicorn app.main:app --reload"
