#!/usr/bin/env bash
# Deploy ROOT backend to Google Cloud Run
# Usage: ./infra/cloudrun/deploy.sh
# Prerequisites:
#   - gcloud auth login
#   - gcloud config set project <PROJECT_ID>
#   - MONGODB_URI stored in Secret Manager as 'mongodb-uri'

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE="root-backend"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}:latest"

echo "Building image: ${IMAGE}"
gcloud builds submit ./backend \
  --tag="${IMAGE}" \
  --project="${PROJECT_ID}"

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image="${IMAGE}" \
  --platform=managed \
  --region="${REGION}" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=5 \
  --memory=1Gi \
  --cpu=2 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-secrets="MONGODB_URI=mongodb-uri:latest" \
  --service-account="root-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"

URL=$(gcloud run services describe "${SERVICE}" \
  --platform=managed \
  --region="${REGION}" \
  --format="value(status.url)")

echo ""
echo "Deployed: ${URL}"
echo "Health check: curl ${URL}/health"
echo ""
echo "Set in Vercel:"
echo "  NEXT_PUBLIC_API_URL=${URL}"
