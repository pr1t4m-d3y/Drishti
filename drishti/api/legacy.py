"""Endpoints that preserve the v1 dashboard API surface (`/api/...`), now backed by the real model.

v1 returned a rule-based 0-100 risk score. Here `risk_score` is the calibrated default probability x 100
for every customer in the database, so existing screens keep working.
Differences, on purpose: no names / cities / income (the public dataset is anonymised), "transactions"
are the six monthly statement lines, and POST /api/interventions records a *proposal* for human approval
instead of marking something as "Sent".
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from drishti.agents.tools.intervention_tools import ACTION_TYPES
from drishti.api.auth import Principal, require_key
from drishti.api.schemas import InterventionOut
from drishti.db.models import Customer, Intervention
from drishti.db.session import session_scope

router = APIRouter(prefix="/api", tags=["v1-compatible"])

FILTERS = {
    "critical": Customer.risk_segment == "CRITICAL",
    "late_payments": Customer.n_delinquent_months > 0,
    "high_credit_util": Customer.util_latest > 0.75,
}
# v1 labels -> v2 segments
SEGMENT_ALIASES = {"SAFE": "LOW", "MEDIUM RISK": "MEDIUM", "HIGH RISK": "HIGH"}


def _summary(c: Customer) -> dict[str, Any]:
    return {
        "id": c.customer_id, "risk_segment": c.risk_segment, "risk_score": round(c.risk_proba * 100, 1),
        "credit_util_pct": round(max(c.util_latest, 0) * 100, 1), "late_payments": c.n_delinquent_months,
        "max_delay_months": c.max_delay, "age": c.age, "credit_limit": c.limit_bal,
        "top_risk_factors": c.top_risk_factors,
    }


@router.get("/stats")
def stats(_: Principal = Depends(require_key)) -> dict:
    with session_scope() as db:
        seg = dict(db.execute(select(Customer.risk_segment, func.count()).group_by(Customer.risk_segment)).all())
        avg_util, late = db.execute(select(func.avg(Customer.util_latest), func.sum(Customer.n_delinquent_months))).one()
    total = sum(seg.values())
    return {
        "totalCustomers": total, "activeAccounts": total, "criticalCount": seg.get("CRITICAL", 0),
        "highRiskCount": seg.get("CRITICAL", 0) + seg.get("HIGH", 0), "mediumCount": seg.get("MEDIUM", 0),
        "safeCount": seg.get("LOW", 0), "avgCreditUtil": round(float(avg_util or 0) * 100, 1),
        "totalLatePayments": int(late or 0), "segments": seg,
    }


@router.get("/customers")
def customers(
    risk: str | None = None, filter: str | None = Query(None, pattern="^(critical|late_payments|high_credit_util)$"),
    search: str | None = Query(None, max_length=20), limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0), _: Principal = Depends(require_key),
) -> dict:
    conds = []
    if risk:
        seg = SEGMENT_ALIASES.get(risk.upper(), risk.upper())
        if seg not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            raise HTTPException(422, "risk must be CRITICAL, HIGH, MEDIUM or LOW")
        conds.append(Customer.risk_segment == seg)
    if filter:
        conds.append(FILTERS[filter])
    if search:
        if not search.isdigit():
            raise HTTPException(422, "search must be a customer id (the dataset has no names)")
        conds.append(Customer.customer_id == int(search))
    with session_scope() as db:
        total = db.scalar(select(func.count()).select_from(Customer).where(*conds))
        rows = db.scalars(select(Customer).where(*conds).order_by(Customer.risk_proba.desc(), Customer.customer_id)
                          .limit(limit).offset(offset)).all()
        return {"customers": [_summary(c) for c in rows], "total": total}


@router.get("/customers/{customer_id}/transactions")
def statement_history(customer_id: int, months: int = Query(6, ge=1, le=6), _: Principal = Depends(require_key)) -> list[dict]:
    """The six monthly statement lines in the dataset (bill, payment, repayment status). No card-level transactions exist."""
    with session_scope() as db:
        c = db.get(Customer, customer_id)
        if c is None:
            raise HTTPException(404, "customer not found")
        return [
            {"months_ago": i, "bill_amount": getattr(c, f"bill_amt{i}"), "payment_amount": getattr(c, f"pay_amt{i}"),
             "repayment_status": getattr(c, f"pay_{i}")}
            for i in range(1, months + 1)
        ]


class InterventionIn(BaseModel):
    customerId: int  # noqa: N815 - v1 field name
    action: str = Field(min_length=1, max_length=32)
    rationale: str = Field(default="Analyst-initiated recommendation", max_length=2000)


@router.post("/interventions", response_model=InterventionOut)
def create_intervention(body: InterventionIn, who: Principal = Depends(require_key)):
    """An analyst records a recommendation. It starts as `proposed`; a different person must approve or reject it (four-eyes)."""
    action = body.action.upper().replace(" ", "_")
    if action not in ACTION_TYPES:
        raise HTTPException(422, f"action must be one of {sorted(ACTION_TYPES)}")
    with session_scope() as db:
        if db.get(Customer, body.customerId) is None:
            raise HTTPException(404, "customer not found")
        row = Intervention(customer_id=body.customerId, action_type=action, rationale=body.rationale,
                           citations=[], status="proposed", proposed_by=who.name)
        db.add(row)
        db.flush()
        return InterventionOut.model_validate(row)


@router.get("/customers/{customer_id}/interventions", response_model=list[InterventionOut])
def customer_interventions(customer_id: int, _: Principal = Depends(require_key)):
    with session_scope() as db:
        rows = db.scalars(select(Intervention).where(Intervention.customer_id == customer_id)
                          .order_by(Intervention.created_at.desc())).all()
        return [InterventionOut.model_validate(r) for r in rows]
