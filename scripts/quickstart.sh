#!/usr/bin/env bash
# Zero to a running local API in one command (no Docker, SQLite). Re-runnable.
set -euo pipefail
cd "$(dirname "$0")/.."
PYBIN=${PYBIN:-python3}
[[ -d .venv ]] || "$PYBIN" -m venv .venv
.venv/bin/python -m pip install -q -r requirements-dev.txt
.venv/bin/python -m drishti.pipeline --no-eval
KEY=$(.venv/bin/python -m drishti.api.auth "local-$(date +%s)" admin | tail -1)
echo
echo "API key (shown once): $KEY"
echo "Start the API:  make api      then:  curl -H 'X-API-Key: $KEY' 'localhost:8000/early-warning?segment=CRITICAL&limit=3'"
.venv/bin/python -m drishti.doctor || true
