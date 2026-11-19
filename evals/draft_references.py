"""Draft reference answers for the policy questions FROM THE INGESTED DOCUMENTS, for human review.

    python -m evals.draft_references            # draft every question still `needs_review`
    python -m evals.draft_references --list     # show status of every policy question
    python -m evals.draft_references --approve pol-01 pol-02   # a human confirms a draft

Rules that keep this honest:
* The model may only use the retrieved passages. If none contain the answer, the question is marked
  `not_in_corpus` (and the expected behaviour becomes "say the corpus does not cover it").
* Drafts are `auto_drafted`, never `reviewed`. Only `--approve` (a human) sets `reviewed`.
* Each draft stores the chunk ids it was written from.
"""

from __future__ import annotations

import argparse
import json

from drishti.config import get_settings
from evals.build_golden_set import OUT
from evals.run import relevant

PROMPT = (
    "Write a reference answer to the QUESTION using ONLY the PASSAGES. Quote or closely paraphrase the "
    "passage text, name the section, and do not add anything not in the passages. If the passages do not "
    "answer the question, reply exactly: NOT_IN_CORPUS\n\nQUESTION: {q}\n\nPASSAGES:\n{p}"
)


def _load() -> list[dict]:
    return [json.loads(x) for x in OUT.read_text().splitlines() if x.strip()]


def _save(qs: list[dict]) -> None:
    OUT.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in qs) + "\n")


def draft(limit: int | None = None) -> dict:
    from google import genai

    from drishti.rag.retrieval import Retriever

    r, client = Retriever(), genai.Client()
    qs, n = _load(), {"auto_drafted": 0, "not_in_corpus": 0}
    for q in qs:
        if q["category"] != "policy" or q.get("status") not in (None, "needs_review"):
            continue
        hits = [h for h in r.search(q["question"], k=5, mode="rerank") if relevant(h.chunk.text, h.chunk.section, q["gold_keywords"])]
        if not hits:
            q["status"], q["reference"] = "not_in_corpus", None
            n["not_in_corpus"] += 1
            continue
        passages = "\n\n".join(f"[{h.chunk.section}, p{h.chunk.page}] {h.chunk.text}" for h in hits)
        out = (client.models.generate_content(model=get_settings().judge_model, contents=PROMPT.format(q=q["question"], p=passages)).text or "").strip()
        if out == "NOT_IN_CORPUS" or not out:
            q["status"], q["reference"] = "not_in_corpus", None
            n["not_in_corpus"] += 1
        else:
            q.update(reference=out, reference_chunks=[h.chunk.chunk_id for h in hits], status="auto_drafted")
            n["auto_drafted"] += 1
        if limit and sum(n.values()) >= limit:
            break
    _save(qs)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--approve", nargs="*")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.approve:
        qs = _load()
        for q in qs:
            if q["id"] in a.approve and q.get("status") == "auto_drafted":
                q["status"] = "reviewed"
        _save(qs)
    if a.list or a.approve:
        for q in _load():
            if q["category"] == "policy":
                print(f"{q['id']}  {q.get('status', '?'):<14} {q['question'][:80]}")
        return
    print(json.dumps(draft(a.limit), indent=2))


if __name__ == "__main__":
    main()
