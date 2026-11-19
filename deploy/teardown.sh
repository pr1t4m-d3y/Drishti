#!/usr/bin/env bash
# Deletes everything deploy.sh created. Asks before doing anything destructive.
set -euo pipefail
: "${PROJECT_ID:?set PROJECT_ID}" "${REGION:?set REGION}"
SERVICE=${SERVICE:-drishti-api}; REPO=${REPO:-drishti}; SQL_INSTANCE=${SQL_INSTANCE:-drishti-pg}
read -r -p "Delete Cloud Run service, Cloud SQL instance (and its data), secrets, registry and service account in $PROJECT_ID? [type yes] " a
[[ "$a" == "yes" ]] || { echo aborted; exit 1; }
gcloud config set project "$PROJECT_ID"
gcloud run jobs delete drishti-bootstrap --region "$REGION" --quiet || true
gcloud run jobs delete drishti-apikey --region "$REGION" --quiet || true
gcloud run services delete "$SERVICE" --region "$REGION" --quiet || true
gcloud sql instances delete "$SQL_INSTANCE" --quiet || true
gcloud secrets delete drishti-db-password --quiet || true
gcloud secrets delete drishti-api-pepper --quiet || true
gcloud artifacts repositories delete "$REPO" --location "$REGION" --quiet || true
gcloud iam service-accounts delete "drishti-run@${PROJECT_ID}.iam.gserviceaccount.com" --quiet || true
echo "Done. Budgets (if created) are under Billing > Budgets and are not deleted here."
