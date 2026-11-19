"""Vector stores for policy chunks.

* `SqliteVectorStore`: local/dev and tests. Vectors stored as float32 BLOBs, cosine via numpy.
* `PgVectorStore`   : production (Cloud SQL for PostgreSQL + pgvector, HNSW index, cosine).

Both expose the same interface, so ingestion, retrieval and evals do not care which is active.
Chunk ids are content hashes, which is what makes ingestion idempotent.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from drishti.config import get_settings


@dataclass
class Chunk:
    doc_id: str
    doc_title: str
    section: str  # e.g. "Chapter III > 12. Grievance redressal"
    clause: str  # e.g. "12" or "12.3" ("" if unknown)
    page: int
    text: str
    chunk_id: str = ""
    embedding: np.ndarray | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.chunk_id:
            raw = f"{self.doc_id}|{self.section}|{self.page}|{self.text}".encode()
            self.chunk_id = hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:16]

    def meta(self) -> dict:
        d = asdict(self)
        d.pop("embedding")
        return d


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk]) -> int: ...
    def delete_doc(self, doc_id: str) -> int: ...
    def all_chunks(self) -> list[Chunk]: ...  # without embeddings (for BM25)
    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[Chunk, float]]: ...
    def get(self, chunk_id: str) -> Chunk | None: ...
    def stats(self) -> dict: ...


class SqliteVectorStore:
    def __init__(self, path: str | Path | None = None, dim: int | None = None):
        s = get_settings()
        url = s.database_url
        self.path = str(path or (url.split("///", 1)[1] if url.startswith("sqlite") else "drishti.sqlite"))
        self.dim = dim or s.embedding_dim
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS policy_chunks(
                chunk_id TEXT PRIMARY KEY, doc_id TEXT, doc_title TEXT, section TEXT,
                clause TEXT, page INTEGER, text TEXT, embedding BLOB)"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS ix_pc_doc ON policy_chunks(doc_id)")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def upsert(self, chunks: list[Chunk]) -> int:
        rows = [
            (c.chunk_id, c.doc_id, c.doc_title, c.section, c.clause, c.page, c.text,
             np.asarray(c.embedding, dtype=np.float32).tobytes())
            for c in chunks
        ]
        with self._conn() as c:
            c.executemany("INSERT OR REPLACE INTO policy_chunks VALUES (?,?,?,?,?,?,?,?)", rows)
        return len(rows)

    def delete_doc(self, doc_id: str) -> int:
        with self._conn() as c:
            return c.execute("DELETE FROM policy_chunks WHERE doc_id=?", (doc_id,)).rowcount

    @staticmethod
    def _row(r: tuple) -> Chunk:
        return Chunk(chunk_id=r[0], doc_id=r[1], doc_title=r[2], section=r[3], clause=r[4], page=r[5], text=r[6])

    def all_chunks(self) -> list[Chunk]:
        with self._conn() as c:
            return [self._row(r) for r in c.execute(
                "SELECT chunk_id,doc_id,doc_title,section,clause,page,text FROM policy_chunks ORDER BY doc_id,page")]

    def get(self, chunk_id: str) -> Chunk | None:
        with self._conn() as c:
            r = c.execute(
                "SELECT chunk_id,doc_id,doc_title,section,clause,page,text FROM policy_chunks WHERE chunk_id=?",
                (chunk_id,)).fetchone()
        return self._row(r) if r else None

    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        with self._conn() as c:
            rows = c.execute("SELECT chunk_id,doc_id,doc_title,section,clause,page,text,embedding FROM policy_chunks").fetchall()
        if not rows:
            return []
        mat = np.vstack([np.frombuffer(r[7], dtype=np.float32) for r in rows])
        sims = mat @ query_vec.astype(np.float32)
        top = np.argsort(-sims)[:k]
        return [(self._row(rows[i]), float(sims[i])) for i in top]

    def stats(self) -> dict:
        with self._conn() as c:
            n_chunks, n_docs = c.execute("SELECT COUNT(*), COUNT(DISTINCT doc_id) FROM policy_chunks").fetchone()
        return {"backend": "sqlite", "documents": n_docs, "chunks": n_chunks}


class PgVectorStore:
    """pgvector-backed store. Schema is created idempotently; HNSW index with cosine ops."""

    def __init__(self, dsn: str | None = None, dim: int | None = None):
        import psycopg
        from pgvector.psycopg import register_vector

        s = get_settings()
        self.dim = dim or s.embedding_dim
        self._dsn = (dsn or s.database_url).replace("+psycopg", "")
        with psycopg.connect(self._dsn, autocommit=True) as c:
            c.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(c)
            c.execute(
                f"""CREATE TABLE IF NOT EXISTS policy_chunks(
                chunk_id TEXT PRIMARY KEY, doc_id TEXT, doc_title TEXT, section TEXT,
                clause TEXT, page INT, text TEXT, embedding vector({self.dim}))"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS ix_pc_doc ON policy_chunks(doc_id)")
            c.execute(
                "CREATE INDEX IF NOT EXISTS ix_pc_hnsw ON policy_chunks USING hnsw (embedding vector_cosine_ops)"
            )

    def _connect(self):
        import psycopg
        from pgvector.psycopg import register_vector

        c = psycopg.connect(self._dsn)
        register_vector(c)
        return c

    def upsert(self, chunks: list[Chunk]) -> int:
        with self._connect() as c, c.cursor() as cur:
            for ch in chunks:
                cur.execute(
                    """INSERT INTO policy_chunks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (chunk_id) DO UPDATE SET text=EXCLUDED.text, embedding=EXCLUDED.embedding""",
                    (ch.chunk_id, ch.doc_id, ch.doc_title, ch.section, ch.clause, ch.page, ch.text,
                     np.asarray(ch.embedding, dtype=np.float32)),
                )
        return len(chunks)

    def delete_doc(self, doc_id: str) -> int:
        with self._connect() as c:
            return c.execute("DELETE FROM policy_chunks WHERE doc_id=%s", (doc_id,)).rowcount

    @staticmethod
    def _row(r) -> Chunk:
        return Chunk(chunk_id=r[0], doc_id=r[1], doc_title=r[2], section=r[3], clause=r[4], page=r[5], text=r[6])

    def all_chunks(self) -> list[Chunk]:
        with self._connect() as c:
            return [self._row(r) for r in c.execute(
                "SELECT chunk_id,doc_id,doc_title,section,clause,page,text FROM policy_chunks ORDER BY doc_id,page")]

    def get(self, chunk_id: str) -> Chunk | None:
        with self._connect() as c:
            r = c.execute("SELECT chunk_id,doc_id,doc_title,section,clause,page,text FROM policy_chunks WHERE chunk_id=%s",
                          (chunk_id,)).fetchone()
        return self._row(r) if r else None

    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        q = query_vec.astype(np.float32)
        with self._connect() as c:
            rows = c.execute(
                """SELECT chunk_id,doc_id,doc_title,section,clause,page,text, 1 - (embedding <=> %s) AS sim
                   FROM policy_chunks ORDER BY embedding <=> %s LIMIT %s""", (q, q, k)).fetchall()
        return [(self._row(r), float(r[7])) for r in rows]

    def stats(self) -> dict:
        with self._connect() as c:
            n_chunks, n_docs = c.execute("SELECT COUNT(*), COUNT(DISTINCT doc_id) FROM policy_chunks").fetchone()
        return {"backend": "pgvector", "documents": n_docs, "chunks": n_chunks}


def get_store() -> VectorStore:
    url = get_settings().database_url
    return PgVectorStore() if url.startswith("postgresql") else SqliteVectorStore()


__all__ = ["Chunk", "VectorStore", "SqliteVectorStore", "PgVectorStore", "get_store", "json"]
