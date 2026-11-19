"""Timed manual-vs-assisted review benchmark. See benchmarks/README.md for the protocol."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import random
import statistics
import time
from pathlib import Path

from sqlalchemy import text

from drishti.agents.tools.intervention_tools import ACTION_TYPES
from drishti.db.session import get_engine

HERE = Path(__file__).parent
TIMINGS = HERE / "results" / "timings.csv"
REFERENCE = HERE / "reference_decisions.csv"
FIELDS = ["participant", "case_id", "customer_id", "segment", "condition", "seconds", "decision"]
MIN_PARTICIPANTS = 3


def pick_cases(n: int) -> list[dict]:
    """Deterministic, stratified: equal share of CRITICAL / HIGH / MEDIUM / LOW, lowest ids first."""
    per = max(1, n // 4)
    cases: list[dict] = []
    with get_engine().connect() as c:
        for seg in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            rows = c.execute(text("SELECT customer_id FROM customers WHERE risk_segment=:s ORDER BY customer_id LIMIT :n OFFSET 100"),
                             {"s": seg, "n": per}).all()
            cases += [{"case_id": f"{seg[:1]}{r[0]}", "customer_id": r[0], "segment": seg} for r in rows]
    return cases[:n]


def assign_conditions(participant: str, cases: list[dict]) -> list[dict]:
    """Counterbalance: alternate manual/assisted, and flip the starting condition by participant hash."""
    flip = int(hashlib.sha256(participant.encode()).hexdigest(), 16) % 2
    order = random.Random(participant).sample(cases, len(cases))  # per-participant case order, reproducible
    return [{**c, "condition": "manual" if (i + flip) % 2 == 0 else "assisted"} for i, c in enumerate(order)]


def _show_manual(customer_id: int) -> None:
    with get_engine().connect() as c:
        row = c.execute(text("SELECT * FROM customers WHERE customer_id=:i"), {"i": customer_id}).mappings().one()
    skip = {"default_label", "top_risk_factors", "scored_at"}
    print("\n".join(f"  {k:>22}: {v}" for k, v in row.items() if k not in skip))
    print("\n  Policy documents are in data/policies/. Look up what is permitted yourself.")


def _show_assisted(customer_id: int) -> None:
    from drishti.agents.runtime import ChatService

    async def go() -> str:
        svc = ChatService()
        final = None
        async for ev in svc.chat("benchmark", f"What can we offer customer #{customer_id} under our policies?"):
            final = ev if ev["type"] == "final" else final
        return final["answer"] if final else ""

    print("\n" + asyncio.run(go()))


def run(participant: str, n_cases: int) -> None:
    TIMINGS.parent.mkdir(parents=True, exist_ok=True)
    new = not TIMINGS.exists()
    allowed = sorted(ACTION_TYPES)
    plan = assign_conditions(participant, pick_cases(n_cases))
    with TIMINGS.open("a", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        if new:
            w.writeheader()
        for i, case in enumerate(plan, 1):
            input(f"\nCase {i}/{len(plan)} ({case['condition']}). Press Enter to show it and start the timer...")
            t0 = time.perf_counter()
            (_show_manual if case["condition"] == "manual" else _show_assisted)(case["customer_id"])
            dec = ""
            while dec not in allowed:
                dec = input(f"Decision {allowed}: ").strip().upper()
            secs = round(time.perf_counter() - t0, 1)
            w.writerow({"participant": participant, "case_id": case["case_id"], "customer_id": case["customer_id"],
                        "segment": case["segment"], "condition": case["condition"], "seconds": secs, "decision": dec})
            fh.flush()
    print("Done. Thank you. Run `python -m benchmarks.review_time analyze` after all participants finish.")


def bootstrap_ci(values: list[float], reps: int = 5000, seed: int = 7) -> tuple[float, float]:
    rng = random.Random(seed)
    stats = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(reps))
    return stats[int(0.025 * reps)], stats[int(0.975 * reps) - 1]


def analyze(path: Path = TIMINGS, reference: Path = REFERENCE) -> dict:
    if not path.exists():
        return {"error": f"no timings at {path}; run the benchmark first"}
    rows = list(csv.DictReader(path.open()))
    by: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        by.setdefault(r["participant"], {"manual": [], "assisted": []})[r["condition"]].append(float(r["seconds"]))
    paired = {p: v for p, v in by.items() if v["manual"] and v["assisted"]}
    out: dict = {
        "participants": len(paired), "reviews": len(rows),
        "median_seconds": {c: statistics.median([float(r["seconds"]) for r in rows if r["condition"] == c] or [float("nan")])
                           for c in ("manual", "assisted")},
    }
    reductions = [100 * (1 - statistics.median(v["assisted"]) / statistics.median(v["manual"])) for v in paired.values()]
    if len(paired) < MIN_PARTICIPANTS:
        out["reduction_pct"] = None
        out["note"] = f"need at least {MIN_PARTICIPANTS} participants with both conditions to report a reduction (have {len(paired)})"
    else:
        lo, hi = bootstrap_ci(reductions)
        out["reduction_pct"] = {"median_of_participants": round(statistics.median(reductions), 1), "ci95": [round(lo, 1), round(hi, 1)]}
    if reference.exists():
        ref = {r["case_id"]: r["decision"].strip().upper() for r in csv.DictReader(reference.open())}
        agree: dict[str, list[bool]] = {"manual": [], "assisted": []}
        for r in rows:
            if r["case_id"] in ref:
                agree[r["condition"]].append(r["decision"] == ref[r["case_id"]])
        out["decision_agreement"] = {c: (round(sum(v) / len(v), 3) if v else None) for c, v in agree.items()}
    return out


def main() -> None:
    import json

    ap = argparse.ArgumentParser(prog="benchmarks.review_time")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--participant", required=True)
    r.add_argument("--cases", type=int, default=6)
    sub.add_parser("analyze")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.participant, a.cases)
    else:
        print(json.dumps(analyze(), indent=2))


if __name__ == "__main__":
    main()
