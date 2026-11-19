locals {
  apis = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudtrace.googleapis.com",
    "billingbudgets.googleapis.com",
  ]
  runtime_roles = [
    "roles/aiplatform.user",
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# --- least-privilege runtime identity ---------------------------------------------------------
resource "google_service_account" "runtime" {
  account_id   = "drishti-run"
  display_name = "Drishti Cloud Run runtime"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(local.runtime_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.runtime.email}"
}

# --- image registry ---------------------------------------------------------------------------
resource "google_artifact_registry_repository" "images" {
  repository_id = "drishti"
  location      = var.region
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# --- Cloud SQL for PostgreSQL (pgvector is enabled by migrations/002_policy_vectors.sql) -------
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "random_password" "pepper" {
  length  = 48
  special = false
}

resource "google_sql_database_instance" "pg" {
  name                = "drishti-pg"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.sql_tier
    availability_type = "ZONAL"
    disk_size         = 10
    backup_configuration {
      enabled = false
    }
    ip_configuration {
      ipv4_enabled = true # reached only through the Cloud SQL connector from Cloud Run
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "app" {
  name     = "drishti"
  instance = google_sql_database_instance.pg.name
}

resource "google_sql_user" "app" {
  name     = "drishti"
  instance = google_sql_database_instance.pg.name
  password = random_password.db.result
}

# --- secrets (values never appear in config or logs) --------------------------------------------
resource "google_secret_manager_secret" "db_password" {
  secret_id = "drishti-db-password"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db.result
}

resource "google_secret_manager_secret" "pepper" {
  secret_id = "drishti-api-pepper"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "pepper" {
  secret      = google_secret_manager_secret.pepper.id
  secret_data = random_password.pepper.result
}

# --- Cloud Run (private by default) --------------------------------------------------------------
resource "google_cloud_run_v2_service" "api" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runtime.email
    timeout         = "120s"

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.pg.connection_name]
      }
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "DRISHTI_ENV"
        value = "prod"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "LLM_MODEL"
        value = var.llm_model
      }
      env {
        name  = "EMBEDDING_BACKEND"
        value = "vertex"
      }
      env {
        name  = "TRACE_EXPORTER"
        value = "gcp"
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql+psycopg://drishti@/drishti?host=/cloudsql/${google_sql_database_instance.pg.connection_name}"
      }
      env {
        name  = "SESSION_DB_URL"
        value = "postgresql+asyncpg://drishti@/drishti?host=/cloudsql/${google_sql_database_instance.pg.connection_name}"
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "API_KEY_PEPPER"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.pepper.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.runtime,
    google_secret_manager_secret_version.db_password,
    google_secret_manager_secret_version.pepper,
    google_sql_database.app,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = toset(var.invoker_members)
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = each.value
}

# --- budget alert (optional) ---------------------------------------------------------------------
resource "google_billing_budget" "budget" {
  count           = var.billing_account == "" ? 0 : 1
  billing_account = var.billing_account
  display_name    = "drishti-budget"

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_usd)
    }
  }
  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
