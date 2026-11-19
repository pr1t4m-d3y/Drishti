"""Engines and sessions. Two engines: read-write (API, loaders) and read-only (agent SQL tools)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from drishti.config import get_settings
from drishti.db.models import Base


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    engine = create_engine(url, future=True, pool_pre_ping=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # pragma: no cover - trivial
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


@lru_cache
def get_readonly_engine() -> Engine:
    """Engine for agent tools. Writes fail at the database, not just in application code."""
    s = get_settings()
    url = s.readonly_database_url or s.database_url
    if url.startswith("sqlite"):
        path = url.split("///", 1)[1]
        return create_engine(f"sqlite:///file:{path}?mode=ro&uri=true", future=True)
    return create_engine(url, future=True, pool_pre_ping=True)


def init_db() -> None:
    """SQLite: create tables from the ORM models. PostgreSQL: apply the versioned SQL migrations."""
    if get_settings().database_url.startswith("postgresql"):
        from drishti.db.migrate import migrate

        migrate()
        return
    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = sessionmaker(get_engine(), expire_on_commit=False, future=True)
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
