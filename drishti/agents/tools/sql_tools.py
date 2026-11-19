"""Risk-data tools: parameterised, allowlisted queries over a read-only connection.

There is NO free-form SQL. The model picks a query by name and supplies typed parameters; the SQL
text lives here, in code review, and values are always bound parameters. `default_label` (ground
truth) is never selected. Tools are plain functions with docstrings so ADK can wrap them directly
and other agents can reuse them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from drishti.db.session import get_readonly_engine

SEGMENTS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
MAX_ROWS = 50

# Columns an agent may read. Anything not here (notably default_label) is unreachable via tools.
SAFE_CUSTOMER_COLS = (
    "customer_id, age, limit_bal, pay_1, pay_2, pay_3, pay_4, pay_5, pay_6, "
    "bill_amt1, pay_amt1, n_delinquent_months, max_delay, util_latest, "
    "risk_proba, risk_segment, top_risk_factors"
)


@dataclass(frozen=True)
class Query:
    sql: str
    params: dict[str, type]  # parameter name -> required python type
    description: str


ALLOWLIST: dict[str, Query] = {
    "customer_by_id": Query(
        f"SELECT {SAFE_CUSTOMER_COLS} FROM customers WHERE customer_id = :customer_id",
        {"customer_id": int},
        "One customer's profile and risk score.",
    ),
    "top_risk": Query(
        f"SELECT {SAFE_CUSTOMER_COLS} FROM customers ORDER BY risk_proba DESC, customer_id LIMIT :n",
        {"n": int},
        "Highest-risk customers by model probability.",
    ),
    "top_risk_in_segment": Query(
        f"SELECT {SAFE_CUSTOMER_COLS} FROM customers WHERE risk_segment = :segment "
        "ORDER BY risk_proba DESC, customer_id LIMIT :n",
        {"segment": str, "n": int},
        "Highest-risk customers inside one segment.",
    ),
    "segment_counts": Query(
        "SELECT risk_segment, COUNT(*) AS customers, ROUND(AVG(risk_proba), 4) AS avg_risk "
        "FROM customers GROUP BY risk_segment ORDER BY avg_risk DESC",
        {},
        "Customer count and mean risk per segment.",
    ),
    "customers_with_missed_payments": Query(
        f"SELECT {SAFE_CUSTOMER_COLS} FROM customers WHERE n_delinquent_months >= :min_months "
        "ORDER BY risk_proba DESC, customer_id LIMIT :n",
        {"min_months": int, "n": int},
        "Customers delinquent in at least N of the last 6 months.",
    ),
    "count_with_missed_payments": Query(
        "SELECT COUNT(*) AS customers FROM customers WHERE n_delinquent_months >= :min_months",
        {"min_months": int},
        "How many customers are delinquent in at least N of the last 6 months.",
    ),
    "intervention_history": Query(
        "SELECT id, action_type, status, created_at FROM interventions "
        "WHERE customer_id = :customer_id ORDER BY created_at DESC LIMIT 20",
        {"customer_id": int},
        "Past recommended interventions for a customer.",
    ),
}


class QueryError(ValueError):
    pass


def validate_params(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Reject unknown queries, missing/extra params and wrong types. Clamp row limits."""
    if name not in ALLOWLIST:
        raise QueryError(f"unknown query '{name}'. Allowed: {sorted(ALLOWLIST)}")
    spec = ALLOWLIST[name].params
    if set(params) != set(spec):
        raise QueryError(f"'{name}' needs exactly {sorted(spec)}, got {sorted(params)}")
    clean: dict[str, Any] = {}
    for key, typ in spec.items():
        val = params[key]
        if isinstance(val, bool) or not isinstance(val, typ):
            try:
                if typ is int and not isinstance(val, bool):
                    val = int(val)
                else:
                    raise TypeError
            except (TypeError, ValueError) as e:
                raise QueryError(f"param '{key}' must be {typ.__name__}") from e
        clean[key] = val
    if "n" in clean:
        clean["n"] = max(1, min(int(clean["n"]), MAX_ROWS))
    if "segment" in clean:
        clean["segment"] = str(clean["segment"]).upper()
        if clean["segment"] not in SEGMENTS:
            raise QueryError(f"segment must be one of {SEGMENTS}")
    if "min_months" in clean and not 0 <= clean["min_months"] <= 6:
        raise QueryError("min_months must be between 0 and 6")
    return clean


def run_allowlisted_query(name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute one allowlisted, parameterised query on the read-only connection."""
    try:
        clean = validate_params(name, params or {})
    except QueryError as e:
        return {"error": str(e)}
    with get_readonly_engine().connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(ALLOWLIST[name].sql), clean)]
    return {"query": name, "row_count": len(rows), "rows": rows}


# ---- ADK-facing tool functions (type hints + docstrings are the tool schema) -------------------

def get_customer(customer_id: int) -> dict[str, Any]:
    """Look up one customer's profile, repayment history and model risk score by customer id."""
    return run_allowlisted_query("customer_by_id", {"customer_id": customer_id})


def top_risk_customers(n: int = 10, segment: str = "") -> dict[str, Any]:
    """List the n highest-risk customers (max 50). Optionally restrict to a segment: CRITICAL, HIGH, MEDIUM or LOW."""
    if segment:
        return run_allowlisted_query("top_risk_in_segment", {"segment": segment, "n": n})
    return run_allowlisted_query("top_risk", {"n": n})


def segment_summary() -> dict[str, Any]:
    """Customer counts and average risk probability for each risk segment."""
    return run_allowlisted_query("segment_counts")


def customers_with_missed_payments(min_months: int = 2, n: int = 10) -> dict[str, Any]:
    """List customers (max 50) who were delinquent in at least `min_months` of the last 6 months."""
    return run_allowlisted_query("customers_with_missed_payments", {"min_months": min_months, "n": n})


def count_missed_payments(min_months: int = 2) -> dict[str, Any]:
    """Count customers who were delinquent in at least `min_months` of the last 6 months."""
    return run_allowlisted_query("count_with_missed_payments", {"min_months": min_months})


def get_intervention_history(customer_id: int) -> dict[str, Any]:
    """Past recommended interventions and their approval status for a customer."""
    return run_allowlisted_query("intervention_history", {"customer_id": customer_id})


RISK_DATA_TOOLS: list[Any] = [
    get_customer,
    top_risk_customers,
    segment_summary,
    customers_with_missed_payments,
    count_missed_payments,
    get_intervention_history,
]
