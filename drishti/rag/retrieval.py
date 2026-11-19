"""Retrieval: vector baseline, BM25, reciprocal-rank fusion and reranking.

`Retriever.search(query, k, mode=...)` supports:
    "vector"  : dense search only (the ablation baseline)
    "hybrid"  : dense + BM25 fused with RRF
    "rerank"  : hybrid, then rerank the fused candidates (the production configuration)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
from rank_bm25 import BM25Okapi

from drishti.rag.embeddings import Embedder, get_embedder
from drishti.rag.store import Chunk, VectorStore, get_store

Mode = Literal["vector", "hybrid", "rerank"]
_TOK = re.compile(r"[a-z0-9]+")
_STOP = frozenset(["the", "a", "an", "of", "to", "in", "and", "or", "for", "is", "are", "be", "by", "on", "with", "as", "at", "it", "that", "this", "from"])


def tokenize(text: str) -> list[str]:
    return [t for t in _TOK.findall(text.lower()) if t not in _STOP]


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int
    source: str  # which stage produced the final score


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion: score(d) = sum_i 1 / (k + rank_i(d)). Rank is 1-based."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for pos, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + pos)
    return scores


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]: ...


class LexicalReranker:
    """Cheap, deterministic reranker: query-term coverage + bigram overlap + heading match.

    Stand-in that runs offline. In the cloud, swap for `GeminiReranker` (LLM scoring) or the
    Vertex AI Ranking API; the interface is identical.
    """

    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        qset, qbi = set(q), set(zip(q, q[1:], strict=False))
        out = []
        for c in chunks:
            t = tokenize(c.text)
            tset, tbi = set(t), set(zip(t, t[1:], strict=False))
            cov = len(qset & tset) / max(len(qset), 1)
            bi = len(qbi & tbi) / max(len(qbi), 1)
            head = len(qset & set(tokenize(c.section))) / max(len(qset), 1)
            out.append((c, 0.6 * cov + 0.3 * bi + 0.1 * head))
        return sorted(out, key=lambda x: -x[1])


class GeminiReranker:
    """LLM pointwise relevance scoring (0-10). Used when cloud credentials are present."""

    def __init__(self, model: str):
        from google import genai

        self._client, self._model = genai.Client(), model

    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        scored = []
        for c in chunks:
            prompt = (
                "Rate 0-10 how directly this passage answers the question. Reply with a number only.\n"
                f"Question: {query}\nPassage: {c.text[:1500]}"
            )
            try:
                r = self._client.models.generate_content(model=self._model, contents=prompt)
                m = re.search(r"\d+(\.\d+)?", r.text or "")
                scored.append((c, float(m.group()) / 10 if m else 0.0))
            except Exception:  # noqa: BLE001 - a failed score must not fail retrieval
                scored.append((c, 0.0))
        return sorted(scored, key=lambda x: -x[1])


class Retriever:
    def __init__(
        self,
        store: VectorStore | None = None,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
    ):
        self.store = store or get_store()
        self.embedder = embedder or get_embedder()
        self.reranker = reranker or LexicalReranker()
        self._bm25: BM25Okapi | None = None
        self._chunks: list[Chunk] = []

    def _ensure_bm25(self) -> None:
        if self._bm25 is None:
            self._chunks = self.store.all_chunks()
            self._bm25 = BM25Okapi([tokenize(f"{c.section} {c.text}") for c in self._chunks] or [[""]])

    def refresh(self) -> None:
        self._bm25 = None

    def _vector(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        return self.store.search(self.embedder.embed_query(query), k)

    def _keyword(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        self._ensure_bm25()
        assert self._bm25 is not None
        if not self._chunks:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        top = np.argsort(-scores)[:k]
        return [(self._chunks[i], float(scores[i])) for i in top if scores[i] > 0]

    def search(self, query: str, k: int = 5, mode: Mode = "rerank", candidates: int = 20) -> list[Hit]:
        if mode == "vector":
            return [Hit(c, s, i + 1, "vector") for i, (c, s) in enumerate(self._vector(query, k))]

        vec, kw = self._vector(query, candidates), self._keyword(query, candidates)
        by_id = {c.chunk_id: c for c, _ in [*vec, *kw]}
        fused = rrf([[c.chunk_id for c, _ in vec], [c.chunk_id for c, _ in kw]])
        order = sorted(fused, key=lambda cid: -fused[cid])
        if mode == "hybrid":
            return [Hit(by_id[cid], fused[cid], i + 1, "rrf") for i, cid in enumerate(order[:k])]

        ranked = self.reranker.rerank(query, [by_id[cid] for cid in order[:candidates]])
        return [Hit(c, s, i + 1, "rerank") for i, (c, s) in enumerate(ranked[:k])]
