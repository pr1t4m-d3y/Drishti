-- Policy corpus chunks with pgvector (HNSW, cosine). Embedding dimension comes from EMBEDDING_DIM.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_chunks (
    chunk_id  TEXT PRIMARY KEY,           -- content hash: makes ingestion idempotent
    doc_id    TEXT NOT NULL,
    doc_title TEXT NOT NULL,
    section   TEXT NOT NULL,              -- "Chapter > clause heading", kept for citations
    clause    TEXT NOT NULL DEFAULT '',
    page      INTEGER NOT NULL,
    text      TEXT NOT NULL,
    embedding vector({{EMBEDDING_DIM}}) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pc_doc ON policy_chunks (doc_id);
CREATE INDEX IF NOT EXISTS ix_pc_hnsw ON policy_chunks USING hnsw (embedding vector_cosine_ops);
-- keyword side of hybrid search can also run in Postgres at larger scale:
CREATE INDEX IF NOT EXISTS ix_pc_fts ON policy_chunks USING gin (to_tsvector('english', section || ' ' || text));
