# secrets/ — drop-in configuration (never committed)

Everything in this folder except this README is git-ignored. Put your files here and Drishti picks them up
automatically (`make doctor` tells you what it found and what is missing).

| File | What it is | How to get it |
|---|---|---|
| `.env` | Settings, one `KEY=value` per line (see `.env.example` at the repo root) | Copy `.env.example` here and fill it in |
| `gcp-service-account.json` | Google Cloud service-account key (Vertex AI user role). Project id is read from it | Cloud Console → IAM → Service Accounts → Keys → Add key → JSON |

**Simplest option (no GCP project needed):** a Gemini API key from https://aistudio.google.com/apikey.
Put `GOOGLE_API_KEY=...` in `secrets/.env`. Drishti then uses the Gemini API instead of Vertex AI.

**Policy PDFs** do not go here: save them in `data/policies/` (see `data/policies/SOURCES.md`).

Optional keys for `secrets/.env`:
```
GOOGLE_API_KEY=            # AI Studio key (alternative to the service account)
GOOGLE_CLOUD_LOCATION=     # Vertex region, e.g. us-central1 (only with the service account)
LLM_MODEL=gemini-3.1-flash-lite
EMBEDDING_BACKEND=auto     # auto | hash | vertex
RERANKER=auto              # auto | lexical | gemini
```
