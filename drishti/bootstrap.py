"""Credential discovery for the drop-in `secrets/` folder.

Order of precedence (first match wins):
  1. Environment already configured (GOOGLE_API_KEY, or GOOGLE_APPLICATION_CREDENTIALS, or
     Vertex vars)  -> left untouched.
  2. secrets/.env with GOOGLE_API_KEY  -> Gemini API mode.
  3. secrets/gcp-service-account.json  -> Vertex AI mode; project id read from the file.
  4. Nothing found -> offline mode (hash embeddings, lexical reranker, no LLM).

`credential_mode()` is what the rest of the code asks; it never prints secret values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / "secrets"
SA_FILE = SECRETS / "gcp-service-account.json"

Mode = Literal["gemini_api", "vertex", "offline"]
_done = False


def bootstrap() -> None:
    """Idempotent: export credentials found in secrets/ into the process environment."""
    global _done
    if _done:
        return
    _done = True
    env_file = SECRETS / ".env"
    if env_file.exists():
        for k, v in dotenv_values(env_file).items():
            if v and k not in os.environ:
                os.environ[k] = v
    if os.environ.get("GOOGLE_API_KEY"):
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "false")
        return
    if SA_FILE.exists() and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SA_FILE)
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path and Path(sa_path).exists():
        try:
            project = json.loads(Path(sa_path).read_text()).get("project_id")
        except (ValueError, OSError):
            project = None
        if project:
            os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


def credential_mode() -> Mode:
    bootstrap()
    if os.environ.get("GOOGLE_API_KEY"):
        return "gemini_api"
    if os.environ.get("GOOGLE_CLOUD_PROJECT") and (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("K_SERVICE")  # K_SERVICE: on Cloud Run
    ):
        return "vertex"
    return "offline"
