"""Versioned SQL migrations for PostgreSQL.  `python -m drishti.db.migrate`

* Files in `migrations/` are applied in name order, each once (recorded in `schema_migrations`).
* `{{NAME}}` placeholders are filled from the environment (EMBEDDING_DIM defaults from settings).
* A file whose first line is `-- requires: VAR` is skipped (and reported) unless VAR is set.
* SQLite (local mode) uses SQLAlchemy `create_all` instead; this runner is a no-op there.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from drishti.config import ROOT, get_settings

MIGRATIONS = ROOT / "migrations"
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render(sql: str, env: dict[str, str]) -> str:
    missing = {m for m in _PLACEHOLDER.findall(sql) if m not in env}
    if missing:
        raise KeyError(f"unset migration variable(s): {sorted(missing)}")
    return _PLACEHOLDER.sub(lambda m: env[m.group(1)].replace("'", "''"), sql)


def required_var(sql: str) -> str | None:
    m = re.match(r"--\s*requires:\s*(\w+)", sql)
    return m.group(1) if m else None


def pending(applied: set[str], directory: Path = MIGRATIONS) -> list[Path]:
    return [p for p in sorted(directory.glob("*.sql")) if p.name not in applied]


def migrate(dsn: str | None = None, env: dict[str, str] | None = None) -> dict[str, list[str]]:
    s = get_settings()
    dsn = (dsn or s.database_url).replace("+psycopg", "")
    if not dsn.startswith("postgresql"):
        return {"applied": [], "skipped": ["not postgres: SQLAlchemy create_all is used"]}
    import psycopg

    env = {"EMBEDDING_DIM": str(s.embedding_dim), **os.environ, **(env or {})}
    done: dict[str, list[str]] = {"applied": [], "skipped": []}
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())")
        applied = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
        for path in pending(applied):
            sql = path.read_text()
            need = required_var(sql)
            if need and not env.get(need):
                done["skipped"].append(f"{path.name} (set {need})")
                continue
            with conn.transaction():
                conn.execute(render(sql, env))  # type: ignore[arg-type]
                conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            done["applied"].append(path.name)
    return done


if __name__ == "__main__":
    import json

    print(json.dumps(migrate(), indent=2))
