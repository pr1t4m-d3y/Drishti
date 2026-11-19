"""One contract, two backends: SQLite always, PostgreSQL + pgvector when TEST_PG_DSN is set (CI does)."""

import os
import uuid

import numpy as np
import pytest

from drishti.rag.embeddings import HashEmbedder
from drishti.rag.store import Chunk, PgVectorStore, SqliteVectorStore

DIM = 256
PG_DSN = os.getenv("TEST_PG_DSN")


@pytest.fixture(params=["sqlite", pytest.param("pgvector", marks=pytest.mark.skipif(not PG_DSN, reason="TEST_PG_DSN not set"))])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteVectorStore(tmp_path / "c.sqlite", dim=DIM)
    s = PgVectorStore(PG_DSN, dim=DIM)
    s.delete_doc("contract")
    return s


def _chunks(n=3):
    emb = HashEmbedder(DIM)
    texts = ["notice before recovery proceedings", "grievance officer acknowledges complaints", "repayment schedule review"]
    cs = [Chunk("contract", "Contract Doc", f"Sec {i}", str(i), i + 1, t) for i, t in enumerate(texts[:n])]
    for c, v in zip(cs, emb.embed_documents(texts[:n]), strict=True):
        c.embedding = v
    return cs, emb


def test_upsert_search_get_roundtrip(store):
    cs, emb = _chunks()
    assert store.upsert(cs) == 3
    hits = store.search(emb.embed_query("recovery notice"), 2)
    assert hits[0][0].text.startswith("notice before recovery") and hits[0][1] >= hits[1][1]
    got = store.get(cs[1].chunk_id)
    assert got and got.section == "Sec 1" and got.page == 2 and got.doc_title == "Contract Doc"
    assert store.get("missing") is None


def test_upsert_is_idempotent_and_delete_doc_removes(store):
    cs, _ = _chunks()
    store.upsert(cs)
    store.upsert(cs)
    assert sum(c.doc_id == "contract" for c in store.all_chunks()) == 3
    assert store.delete_doc("contract") == 3
    assert not [c for c in store.all_chunks() if c.doc_id == "contract"]


def test_stats_shape(store):
    cs, _ = _chunks()
    store.upsert(cs)
    st = store.stats()
    assert st["chunks"] >= 3 and st["documents"] >= 1 and st["backend"] in {"sqlite", "pgvector"}
    store.delete_doc("contract")


def test_search_empty_store_returns_nothing(tmp_path):
    assert SqliteVectorStore(tmp_path / "e.sqlite", dim=DIM).search(np.ones(DIM, np.float32), 3) == []


@pytest.mark.skipif(not PG_DSN, reason="TEST_PG_DSN not set")
def test_postgres_migrations_apply_once_and_readonly_role_is_locked_down():
    import psycopg

    from drishti.db.migrate import migrate

    admin_dsn = PG_DSN.replace("+psycopg", "")  # type: ignore[union-attr]
    db = "t_" + uuid.uuid4().hex[:8]
    with psycopg.connect(admin_dsn, autocommit=True) as c:
        c.execute(f"CREATE DATABASE {db}")
    dsn = admin_dsn.rsplit("/", 1)[0] + "/" + db
    try:
        first = migrate(dsn, {"READONLY_PASSWORD": "ro_test_pw", "EMBEDDING_DIM": str(DIM)})
        assert len(first["applied"]) == 3 and not first["skipped"]
        again = migrate(dsn, {"READONLY_PASSWORD": "ro_test_pw", "EMBEDDING_DIM": str(DIM)})
        assert again["applied"] == []  # idempotent
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute("INSERT INTO customers VALUES (1,1e5,1,2,1,30,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0.1,0.2,'LOW','[]',now(),1)")
        host = dsn.split("@")[1]
        ro = psycopg.connect(f"postgresql://drishti_ro:ro_test_pw@{host}", autocommit=True)
        assert ro.execute("SELECT risk_segment FROM customers WHERE customer_id=1").fetchone()[0] == "LOW"
        for bad in ("SELECT default_label FROM customers", "DELETE FROM customers", "SELECT * FROM api_keys"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                ro.execute(bad)
        with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(dsn, autocommit=True) as c:
            c.execute("INSERT INTO interventions (customer_id, action_type, rationale, proposed_by, decided_by) VALUES (1,'NO_ACTION','x','a','a')")
        ro.close()
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as c:
            c.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")
