"""Embedding backends.

* `HashEmbedder`  : offline, deterministic feature hashing. Used for tests and for running the
                    pipeline with no cloud credentials. Weaker than a neural model: say so in results.
* `VertexEmbedder`: Gemini embeddings through Vertex AI (google-genai SDK).
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from drishti.config import get_settings

_TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    dim: int
    name: str

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


def _normalize(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.clip(n, 1e-12, None)


class HashEmbedder:
    name = "hash-v1"

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        toks = _TOKEN.findall(text.lower())
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:], strict=False)]
        v = np.zeros(self.dim, dtype=np.float32)
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        return v

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.vstack([self._vec(t) for t in texts])) if texts else np.zeros((0, self.dim), np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


class VertexEmbedder:
    """Calls the embeddings endpoint in batches. Requires GOOGLE_CLOUD_PROJECT / ADC or an API key."""

    def __init__(self, model: str, dim: int):
        from google import genai  # imported lazily so offline mode needs no credentials

        self._client = genai.Client()
        self._model, self.dim, self.name = model, dim, f"vertex:{model}"

    def _embed(self, texts: list[str], task: str) -> np.ndarray:
        from google.genai import types

        out: list[list[float]] = []
        for i in range(0, len(texts), 100):
            res = self._client.models.embed_content(
                model=self._model,
                contents=list(texts[i : i + 100]),  # type: ignore[arg-type]
                config=types.EmbedContentConfig(task_type=task, output_dimensionality=self.dim),
            )
            out.extend(e.values for e in (res.embeddings or []) if e.values is not None)
        return _normalize(np.asarray(out, dtype=np.float32))

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed([text], "RETRIEVAL_QUERY")[0]


def resolved_backend() -> str:
    from drishti.bootstrap import credential_mode

    s = get_settings()
    if s.embedding_backend == "auto":
        return "vertex" if credential_mode() != "offline" else "hash"
    return s.embedding_backend


def get_embedder() -> Embedder:
    s = get_settings()
    if resolved_backend() == "vertex":
        return VertexEmbedder(s.embedding_model, s.embedding_dim)
    return HashEmbedder(s.embedding_dim)
