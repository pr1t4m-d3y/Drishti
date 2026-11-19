"""Ingestion CLI.

    python -m ingest run            # parse -> chunk -> embed -> store (idempotent)
    python -m ingest fetch          # download the RBI corpus (real, public) into data/policies/
    python -m ingest run --reset    # drop and rebuild every document
    python -m ingest stats          # what is in the store

Idempotency: a chunk id is a hash of (doc, section, page, text). Re-running upserts the same ids,
and documents whose file hash changed are deleted and re-ingested, so no duplicates or stale chunks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from drishti.config import get_settings
from drishti.rag.embeddings import get_embedder
from drishti.rag.store import get_store
from ingest.chunk import chunk_document
from ingest.parse import parse_pdf, parse_text

SUPPORTED = {".pdf": parse_pdf, ".txt": parse_text}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run(policies_dir: Path | None = None, reset: bool = False) -> dict:
    policies_dir = policies_dir or get_settings().policies_dir
    store, embedder = get_store(), get_embedder()
    manifest_path = policies_dir / ".ingest_manifest.json"
    manifest = {} if reset or not manifest_path.exists() else json.loads(manifest_path.read_text())
    if manifest.get("_embedder") != embedder.name:  # vectors from a different model are not comparable
        manifest = {}

    files = sorted(p for p in policies_dir.glob("*") if p.suffix.lower() in SUPPORTED)
    report: dict = {"files_found": len(files), "ingested": [], "skipped_unchanged": [], "chunks_written": 0}
    for path in files:
        digest = file_hash(path)
        if manifest.get(path.name) == digest:
            report["skipped_unchanged"].append(path.name)
            continue
        title, pages = SUPPORTED[path.suffix.lower()](path)
        chunks = chunk_document(path.stem, title, pages)
        if not chunks:
            report["ingested"].append({"file": path.name, "chunks": 0, "warning": "no extractable text"})
            continue
        vecs = embedder.embed_documents([f"{c.section}\n{c.text}" for c in chunks])
        for c, v in zip(chunks, vecs, strict=True):
            c.embedding = v
        store.delete_doc(path.stem)  # replace, never duplicate
        report["chunks_written"] += store.upsert(chunks)
        report["ingested"].append({"file": path.name, "chunks": len(chunks), "pages": len(pages)})
        manifest[path.name] = digest
    manifest["_embedder"] = embedder.name
    manifest_path.write_text(json.dumps(manifest, indent=2))
    report["store"] = store.stats()
    report["embedder"] = embedder.name
    return report


def main() -> None:
    ap = argparse.ArgumentParser(prog="ingest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--reset", action="store_true")
    sub.add_parser("stats")
    sub.add_parser("fetch", help="download the RBI policy corpus into data/policies/")
    args = ap.parse_args()
    if args.cmd == "fetch":
        from ingest.fetch import run as fetch_run

        fetch_run()
    elif args.cmd == "run":
        print(json.dumps(run(reset=args.reset), indent=2))
    else:
        print(json.dumps(get_store().stats(), indent=2))


if __name__ == "__main__":
    main()
