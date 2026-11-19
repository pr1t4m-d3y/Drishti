"""Central configuration. Everything environment-specific comes from env vars / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    drishti_env: str = "local"
    database_url: str = f"sqlite:///{ROOT / 'drishti.sqlite'}"
    # Separate, read-only connection for agent SQL tools. In Postgres this is the
    # `drishti_ro` role (see drishti/db/ro_role.sql). For SQLite we open mode=ro.
    readonly_database_url: str | None = None
    session_db_url: str = f"sqlite+aiosqlite:///{ROOT / 'sessions.sqlite'}"

    llm_model: str = "gemini-3.1-flash-lite"
    judge_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_backend: str = "hash"  # "hash" (offline, deterministic) | "vertex"
    embedding_dim: int = 768

    trace_exporter: str = "console"  # console | otlp | gcp | none
    api_key_pepper: str = "change-me"
    rate_limit: str = "30/minute"
    llm_verifier: bool = False  # extra LLM groundedness check on top of the deterministic verifier

    # Risk segment cut-offs on calibrated default probability.
    seg_critical: float = 0.60
    seg_high: float = 0.40
    seg_medium: float = 0.25

    db_password: str | None = None  # injected from Secret Manager; keeps passwords out of DSN env vars

    @model_validator(mode="after")
    def _inject_db_password(self) -> Settings:
        if self.db_password:
            for field in ("database_url", "session_db_url", "readonly_database_url"):
                url = getattr(self, field)
                if url and url.startswith("postgresql"):
                    setattr(self, field, make_url(url).set(password=self.db_password).render_as_string(hide_password=False))
        return self

    model_path: Path = ROOT / "models" / "risk_model.joblib"
    metrics_path: Path = ROOT / "models" / "metrics.json"
    policies_dir: Path = ROOT / "data" / "policies"
    pricing_path: Path = ROOT / "drishti" / "obs" / "pricing.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
