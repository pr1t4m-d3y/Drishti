import pytest

from drishti.rag.embeddings import HashEmbedder
from drishti.rag.retrieval import LexicalReranker, Retriever, rrf, tokenize
from drishti.rag.store import Chunk, SqliteVectorStore
from ingest.__main__ import run
from ingest.chunk import chunk_document
from ingest.parse import Page, clean_page_text, parse_text


def test_clean_page_text_removes_artifacts():
    raw = "Recov-\nery notice\n  12  \nPage 3 of 40\nreal   line"
    assert clean_page_text(raw) == "Recovery notice\nreal line"


def test_chunking_keeps_headings_and_clauses(policy_dir):
    title, pages = parse_text(policy_dir / "fixture_doc.txt")
    chunks = chunk_document("fixture_doc", title, pages)
    by_clause = {c.clause: c for c in chunks}
    assert set(by_clause) == {"5", "6", "7"}
    assert by_clause["5"].section.startswith("CHAPTER II") and "Notice before recovery" in by_clause["5"].section
    assert by_clause["7"].section.startswith("CHAPTER III")
    assert all(c.page == 1 and len(c.text) >= 40 for c in chunks)


def test_long_clause_split_with_overlap():
    long_text = "5. Big clause\n" + " ".join(f"Sentence number {i} is here." for i in range(200))
    chunks = chunk_document("d", "D", [Page(1, long_text)])
    assert len(chunks) > 1 and all(c.clause == "5" and len(c.text) <= 1700 for c in chunks)


def test_chunk_ids_are_deterministic():
    a, b = Chunk("d", "D", "s", "1", 1, "same text"), Chunk("d", "D", "s", "1", 1, "same text")
    assert a.chunk_id == b.chunk_id
    assert Chunk("d", "D", "s", "1", 2, "same text").chunk_id != a.chunk_id


def test_rrf_math():
    s = rrf([["a", "b"], ["b", "c"]], k=60)
    assert s["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert max(s, key=s.get) == "b"


def test_ingest_is_idempotent(policy_dir, tmp_path, monkeypatch):
    from drishti.config import get_settings

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ing.sqlite'}")
    get_settings.cache_clear()
    first = run(policy_dir)
    n = first["store"]["chunks"]
    assert n == 3 and first["chunks_written"] == 3
    second = run(policy_dir)
    assert second["skipped_unchanged"] == ["fixture_doc.txt"] and second["store"]["chunks"] == n
    third = run(policy_dir, reset=True)
    assert third["store"]["chunks"] == n  # replaced, not duplicated
    get_settings.cache_clear()


def _store_with_docs(tmp_path):
    emb = HashEmbedder(256)
    store = SqliteVectorStore(tmp_path / "r.sqlite", dim=256)
    docs = [
        ("a", "Written notice must precede recovery proceedings and state the amount due."),
        ("b", "A grievance officer must acknowledge complaints within a stated number of days."),
        ("c", "Repayment schedule review may be requested by a borrower under documented financial stress."),
    ]
    chunks = [Chunk("d", "Doc", f"Sec {i}", i, 1, t) for i, t in docs]
    for c, v in zip(chunks, emb.embed_documents([c.text for c in chunks]), strict=True):
        c.embedding = v
    store.upsert(chunks)
    return store, emb


@pytest.mark.parametrize("mode", ["vector", "hybrid", "rerank"])
def test_retrieval_modes_find_relevant_chunk(tmp_path, mode):
    store, emb = _store_with_docs(tmp_path)
    r = Retriever(store, emb, LexicalReranker())
    hits = r.search("notice before recovery proceedings", k=2, mode=mode)
    assert hits and "recovery" in hits[0].chunk.text
    assert [h.rank for h in hits] == list(range(1, len(hits) + 1))


def test_tokenize_drops_stopwords():
    assert tokenize("The notice of the recovery") == ["notice", "recovery"]
