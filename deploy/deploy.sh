#!/usr/bin/env bash
# Reproducible Cloud Run deployment. Idempotent: safe to re-run.
#   export PROJECT_ID=... REGION=... BILLING_ACCOUNT=...   (BILLING_ACCOUNT only for the budget alert)
#   bash deploy/deploy.sh
# Nothing here has been executed against a real project by the author yet. Read deploy/README.md first.
set -euo pipefail
: "${PROJECT_ID:?set PROJECT_ID}" "${REGION:?set REGION}"
SERVICE=${SERVICE:-drishti-api}
REPO=${REPO:-drishti}
SQL_INSTANCE=${SQL_INSTANCE:-drishti-pg}
SA=drishti-run@${PROJECT_ID}.iam.gserviceaccount.com
IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:$(git rev-parse --short HEAD)

gcloud config set project "$PROJECT_ID"

echo "== enable APIs"
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com \
  cloudtrace.googleapis.com billingbudgets.googleapis.com

echo "== least-privilege service account"
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 || \
  gcloud iam service-accounts create drishti-run --display-name "Drishti Cloud Run runtime"
for role in roles/aiplatform.user roles/cloudsql.client roles/secretmanager.secretAccessor roles/cloudtrace.agent; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$SA" --role "$role" --condition=None >/dev/null
done

echo "== Cloud SQL for PostgreSQL (smallest tier; pgvector is created by the app with CREATE EXTENSION)"
gcloud sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1 || \
  gcloud sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_16 --tier=db-f1-micro \
    --region "$REGION" --storage-size=10GB --no-backup
gcloud sql databases create drishti --instance "$SQL_INSTANCE" 2>/dev/null || true

echo "== secrets (generated once, never printed or committed)"
mk_secret() {  # name, generator
  gcloud secrets describe "$1" >/dev/null 2>&1 || { eval "$2" | gcloud secrets create "$1" --data-file=-; }
}
mk_secret drishti-db-password "openssl rand -base64 24 | tr -d '/+=\n'"
mk_secret drishti-api-pepper  "openssl rand -base64 32"
gcloud sql users create drishti --instance "$SQL_INSTANCE" --password "$(gcloud secrets versions access latest --secret drishti-db-password)" 2>/dev/null || \
  gcloud sql users set-password drishti --instance "$SQL_INSTANCE" --password "$(gcloud secrets versions access latest --secret drishti-db-password)"

echo "== image"
gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location "$REGION"
gcloud builds submit --tag "$IMAGE" .

echo "== Cloud Run (private: requires an IAM identity; put IAP in front for browser users)"
CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
gcloud run deploy "$SERVICE" --image "$IMAGE" --region "$REGION" --service-account "$SA" \
  --no-allow-unauthenticated --min-instances 0 --max-instances 3 --memory 1Gi --cpu 1 --timeout 120 \
  --add-cloudsql-instances "$CONN" \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},TRACE_EXPORTER=gcp,EMBEDDING_BACKEND=vertex,DRISHTI_ENV=prod" \
  --set-secrets "API_KEY_PEPPER=drishti-api-pepper:latest,DB_PASSWORD=drishti-db-password:latest" \
  --set-env-vars "^@^DATABASE_URL=postgresql+psycopg://drishti@/drishti?host=/cloudsql/${CONN}@SESSION_DB_URL=postgresql+asyncpg://drishti@/drishti?host=/cloudsql/${CONN}"
# The URLs carry no password: the app injects DB_PASSWORD (from Secret Manager) at startup.

if [[ -n "${BILLING_ACCOUNT:-}" ]]; then
  echo "== budget alert (USD ${BUDGET_USD:-20}, alerts at 50/90/100%)"
  gcloud billing budgets create --billing-account "$BILLING_ACCOUNT" --display-name "drishti-budget" \
    --budget-amount "${BUDGET_USD:-20}USD" \
    --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 || true
fi

echo "Deployed. URL:"; gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)'
