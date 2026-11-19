# Deploying to Google Cloud Run

**Status: scripts written, not yet executed against a real project.** Read them before running.

## Prerequisites
* A GCP project with billing, the `gcloud` CLI authenticated (`gcloud auth login`), and Docker not required (Cloud Build builds the image).
* Choose a region where the chosen Gemini model is available on Vertex AI.

## Steps
```bash
export PROJECT_ID=your-project REGION=your-region
export BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX BUDGET_USD=20   # optional: creates a budget alert
bash deploy/deploy.sh
```
The script: enables APIs, creates a least-privilege service account (`aiplatform.user`, `cloudsql.client`,
`secretmanager.secretAccessor`, `cloudtrace.agent`), the smallest Cloud SQL for PostgreSQL instance, secrets in
Secret Manager (never printed), builds the image, deploys Cloud Run **private** (`--no-allow-unauthenticated`,
min instances 0) and creates budget alerts at 50/90/100%.

After deploy, once (from a machine with the Cloud SQL Auth Proxy): load data and policies, then create an API key.
```bash
python -m drishti.ml.train && python -m drishti.db.load && python -m ingest run
python -m drishti.api.auth my-analyst admin     # prints the key once; only its hash is stored
```
Call it with an identity token: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" -H "X-API-Key: $KEY" $URL/health`.
For browser users put Identity-Aware Proxy in front and set `DRISHTI_AUTH=iam`.

Postgres read-only role for the agents: `psql -f migrations/003_readonly_role.sql -v ro_password=...`, then set `READONLY_DATABASE_URL`.

## Teardown
```bash
bash deploy/teardown.sh      # asks for confirmation, deletes service, Cloud SQL, secrets, registry, service account
```
Budgets are not deleted (Billing > Budgets).

## Cost notes
Cloud SQL `db-f1-micro` and a Cloud Run service scaled to zero keep idle cost low, but Cloud SQL bills while it exists. Run teardown when finished.
