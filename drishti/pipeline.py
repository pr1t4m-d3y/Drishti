"""One command from a clean clone to a finished evaluation: `python -m drishti.pipeline` (`make all`).

Steps are skipped when their output already exists (use --force to redo). Steps that need something
the user has not provided yet (credentials, policy PDFs) are reported as SKIPPED with the fix, never
silently faked. Nothing here writes numbers by hand.
"""

from __future__ import annotations

import argparse
import sys
import time

from drishti.bootstrap import credential_mode
from drishti.config import get_settings


def _step(name: str, fn, *, skip: str | None = None) -> str:
    if skip:
        print(f"-- {name}: SKIPPED ({skip})")
        return "skipped"
    t0 = time.perf_counter()
    print(f"-- {name}: running")
    fn()
    print(f"-- {name}: done in {time.perf_counter() - t0:.1f}s")
    return "done"


def run(force: bool = False, full_eval: bool = True) -> dict[str, str]:
    from drishti.db.load import load_customers
    from drishti.db.session import init_db
    from drishti.ml import train
    from drishti.ml.data import RAW_XLS, download_uci

    s = get_settings()
    res: dict[str, str] = {}
    res["data"] = _step("download dataset", download_uci, skip="already present" if RAW_XLS.exists() and not force else None)
    res["train"] = _step("train model", train.main, skip="model exists" if s.model_path.exists() and not force else None)
    init_db()
    res["load"] = _step("score + load customers", load_customers)

    import ingest.__main__ as ing

    pdfs = [p for p in s.policies_dir.glob("*") if p.suffix.lower() in {".pdf", ".txt"}]
    res["ingest"] = _step("ingest policies", lambda: print(ing.run(reset=force)), skip=None if pdfs else "no files in data/policies/ (see SOURCES.md)")

    from evals import build_golden_set
    from evals import run as ev

    res["golden"] = _step("build golden set", build_golden_set.main)
    res["eval_offline"] = _step("offline eval", lambda: ev.main_offline())
    mode = credential_mode()
    if full_eval:
        for variant in ("baseline", "final"):
            res[f"eval_{variant}"] = _step(
                f"end-to-end eval: {variant}", lambda v=variant: ev.main_variant(v, judge=True),
                skip=None if mode != "offline" else "no LLM credentials (see secrets/README.md)",
            )
    res["report"] = _step("write RESULTS.md", ev.write_report)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-eval", action="store_true", help="stop after the offline eval")
    args = ap.parse_args()
    res = run(force=args.force, full_eval=not args.no_eval)
    print("\nSummary:", ", ".join(f"{k}={v}" for k, v in res.items()))
    print("Run `python -m drishti.doctor` to see anything still missing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
