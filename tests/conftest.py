"""Test environment: isolated temp databases, offline embeddings, no tracing, no cloud calls."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="drishti-tests-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{_TMP / 'test.sqlite'}",
    SESSION_DB_URL=f"sqlite+aiosqlite:///{_TMP / 'sessions.sqlite'}",
    EMBEDDING_BACKEND="hash",
    EMBEDDING_DIM="256",
    TRACE_EXPORTER="none",
    API_KEY_PEPPER="test-pepper",
    GOOGLE_API_KEY="test-not-used",
)

import pytest  # noqa: E402

from drishti.config import get_settings  # noqa: E402
from drishti.db.models import Customer  # noqa: E402
from drishti.db.session import get_engine, get_readonly_engine, init_db, session_scope  # noqa: E402


def _customer(cid: int, proba: float, seg: str, delinq: int) -> Customer:
    base = dict(limit_bal=100000.0, sex=1, education=2, marriage=1, age=35)
    pays = {f"pay_{i}": (2 if i <= delinq else 0) for i in range(1, 7)}
    bills = {f"bill_amt{i}": 50000.0 for i in range(1, 7)}
    pamts = {f"pay_amt{i}": 1000.0 for i in range(1, 7)}
    return Customer(
        customer_id=cid, **base, **pays, **bills, **pamts, n_delinquent_months=delinq,
        max_delay=2 if delinq else 0, util_latest=0.5, risk_proba=proba, risk_segment=seg,
        top_risk_factors=[{"feature": "pay_1", "label": "repayment status last month", "impact": 0.9}],
        default_label=1 if proba > 0.5 else 0,
    )


@pytest.fixture(scope="session", autouse=True)
def _db():
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_readonly_engine.cache_clear()
    init_db()
    with session_scope() as db:
        db.add_all(
            [
                _customer(1, 0.91, "CRITICAL", 4),
                _customer(2, 0.75, "CRITICAL", 3),
                _customer(3, 0.45, "HIGH", 2),
                _customer(4, 0.30, "MEDIUM", 1),
                _customer(5, 0.05, "LOW", 0),
                _customer(6, 0.08, "LOW", 0),
            ]
        )
    yield


@pytest.fixture()
def policy_dir(tmp_path: Path) -> Path:
    """TEST FIXTURE ONLY: invented text used to exercise parsing/chunking. It is not RBI policy
    and is never ingested into the real corpus."""
    d = tmp_path / "policies"
    d.mkdir()
    (d / "fixture_doc.txt").write_text(
        "CHAPTER II - Fixture Fair Practices\n"
        "5. Notice before recovery\n"
        "Fixture rule alpha: the lender shall give written notice before starting recovery proceedings "
        "against a borrower, and the notice must state the amount due and the cure period.\n"
        "6. Grievance handling\n"
        "Fixture rule beta: every lender shall maintain a grievance officer whose contact details "
        "are displayed, and complaints must be acknowledged within a stated number of days.\n"
        "CHAPTER III - Fixture Restructuring\n"
        "7. Eligibility for restructuring\n"
        "Fixture rule gamma: a borrower with documented financial stress may request a review of "
        "repayment schedule; the lender must record the reasons for approval or rejection.\n"
    )
    return d
