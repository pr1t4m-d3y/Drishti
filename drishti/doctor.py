"""`python -m drishti.doctor [--ping]`: what is set up, what is missing, and exactly how to fix it."""

from __future__ import annotations

import json
import sys

from sqlalchemy import text

from drishti.bootstrap import SA_FILE, SECRETS, credential_mode
from drishti.config import get_settings
from drishti.ml.data import RAW_XLS

OK, WARN, FAIL = "ok", "warn", "MISSING"


def _db_count(sql: str) -> int | None:
    try:
        from drishti.db.session import get_engine

        with get_engine().connect() as c:
            return int(c.execute(text(sql)).scalar_one())
    except Exception:  # noqa: BLE001
        return None


def checks(ping: bool = False) -> list[tuple[str, str, str, str]]:
    """(name, status, detail, fix)"""
    s = get_settings()
    out: list[tuple[str, str, str, str]] = []
    mode = credential_mode()
    out.append((
        "LLM credentials", OK if mode != "offline" else WARN,
        {"gemini_api": "Gemini API key found", "vertex": "Vertex AI service account found", "offline": "none found (offline mode)"}[mode],
        f"Put GOOGLE_API_KEY=... in {SECRETS / '.env'} or drop {SA_FILE.name} in {SECRETS}/ (see secrets/README.md)",
    ))
    out.append(("Dataset", OK if RAW_XLS.exists() else FAIL, str(RAW_XLS.name), "make data"))
    out.append(("Trained model", OK if s.model_path.exists() else FAIL, str(s.model_path.name), "make train"))
    n = _db_count("SELECT COUNT(*) FROM customers")
    out.append(("Customers loaded", OK if n else FAIL, f"{n or 0:,} rows", "make load"))
    pdfs = sorted(p.name for p in s.policies_dir.glob("*") if p.suffix.lower() in {".pdf", ".txt"})
    out.append(("Policy documents", OK if pdfs else FAIL, f"{len(pdfs)} file(s)", "Save the RBI PDFs into data/policies/ (see SOURCES.md)"))
    chunks = _db_count("SELECT COUNT(*) FROM policy_chunks")
    out.append(("Policy chunks ingested", OK if chunks else (WARN if not pdfs else FAIL), f"{chunks or 0:,} chunks", "make ingest"))
    if (RAW := s.policies_dir / ".ingest_manifest.json").exists():
        emb = json.loads(RAW.read_text()).get("_embedder", "?")
        out.append(("Embedder used for ingest", OK, emb, "Re-run `make ingest` after changing EMBEDDING_BACKEND"))
    golden_review = _golden_review_counts()
    out.append(("Golden-set policy references", OK if golden_review[1] == 0 else WARN,
                f"{golden_review[0]} reviewed, {golden_review[1]} awaiting review", "make drafts, then review evals/golden_set.jsonl"))
    if ping and mode != "offline":
        out.append(_ping_llm())
    return out


def _golden_review_counts() -> tuple[int, int]:
    from evals.run import load_golden

    pol = [q for q in load_golden() if q["category"] == "policy"]
    needs = sum(q.get("status") in ("needs_review", "auto_drafted") for q in pol)
    return len(pol) - needs, needs


def _ping_llm() -> tuple[str, str, str, str]:
    try:
        from google import genai

        r = genai.Client().models.generate_content(model=get_settings().llm_model, contents="Reply with the single word: pong")
        return ("LLM round-trip", OK if "pong" in (r.text or "").lower() else WARN, (r.text or "").strip()[:40], "check model name / quota")
    except Exception as e:  # noqa: BLE001
        return ("LLM round-trip", FAIL, type(e).__name__ + ": " + str(e)[:120], "check credentials, region and LLM_MODEL")


def main() -> int:
    rows = checks(ping="--ping" in sys.argv)
    w = max(len(r[0]) for r in rows)
    for name, status, detail, fix in rows:
        line = f"[{status:>7}] {name:<{w}}  {detail}"
        print(line + (f"\n{'':>10}{'':<{w}}  -> {fix}" if status != OK else ""))
    blocking = [r for r in rows if r[1] == FAIL and r[0] in {"Dataset", "Trained model", "Customers loaded"}]
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
