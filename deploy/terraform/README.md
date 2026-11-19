# Terraform

Reproducible infrastructure for Drishti: APIs, least-privilege service account, Artifact Registry, Cloud SQL for
PostgreSQL, Secret Manager secrets (random, never in state outputs), a private Cloud Run service and an optional budget alert.
This is the declarative alternative to `deploy/deploy.sh`; use one or the other.

```bash
cd deploy/terraform
terraform init
# 1) create the registry first so an image can be pushed
terraform apply -target=google_artifact_registry_repository.images -var project_id=$PROJECT_ID -var region=$REGION -var image=placeholder
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/drishti/drishti-api:v1 ../..
# 2) everything else
terraform apply -var project_id=$PROJECT_ID -var region=$REGION \
  -var image=$REGION-docker.pkg.dev/$PROJECT_ID/drishti/drishti-api:v1 \
  -var 'invoker_members=["user:you@example.com"]' -var billing_account=XXXXXX-XXXXXX-XXXXXX
```
Teardown: `terraform apply -var deletion_protection=false ... && terraform destroy ...`.

Status: written and syntax-checked in CI (`tests/test_terraform.py`); not yet applied to a real project.
