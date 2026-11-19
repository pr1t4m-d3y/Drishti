variable "project_id" {
  description = "GCP project id"
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, Cloud SQL and Artifact Registry (must offer the chosen Gemini model on Vertex AI)"
  type        = string
}

variable "image" {
  description = "Container image to deploy, e.g. REGION-docker.pkg.dev/PROJECT/drishti/drishti-api:TAG (build with `gcloud builds submit`)"
  type        = string
}

variable "service_name" {
  type    = string
  default = "drishti-api"
}

variable "llm_model" {
  type    = string
  default = "gemini-3.1-flash-lite"
}

variable "invoker_members" {
  description = "IAM members allowed to call the service, e.g. [\"user:you@example.com\"]. Empty = nobody (private)."
  type        = list(string)
  default     = []
}

variable "sql_tier" {
  description = "Cloud SQL machine tier. db-f1-micro is the cheapest; fine for a pilot."
  type        = string
  default     = "db-f1-micro"
}

variable "deletion_protection" {
  description = "Protect Cloud SQL from accidental `terraform destroy`. Set false when you really want to tear down."
  type        = bool
  default     = true
}

variable "billing_account" {
  description = "Billing account id to attach a budget alert to. Empty = no budget."
  type        = string
  default     = ""
}

variable "budget_usd" {
  type    = number
  default = 20
}
