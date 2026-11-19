"""Intervention tools: explain a customer's risk and *propose* (never execute) an action.

`propose_intervention` is the only write tool in the whole system. It inserts a row with status
'proposed'. A human must approve it through the API; nothing downstream acts on it automatically.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from drishti.agents.tools.sql_tools import get_customer
from drishti.db.models import Customer, Intervention
from drishti.db.session import session_scope
from drishti.rag.store import get_store

ACTION_TYPES = {
    "EMI_EXTENSION": "Short extension of the EMI / payment due date",
    "RESTRUCTURING_REVIEW": "Refer the account for formal restructuring review",
    "COUNSELLING_REFERRAL": "Refer the customer to financial counselling",
    "PAYMENT_REMINDER": "Proactive reminder / outreach before the due date",
    "NO_ACTION": "No intervention warranted at present",
}


def get_risk_factors(customer_id: int) -> dict[str, Any]:
    """Explain why a customer is at risk: model drivers plus delinquency and utilisation facts."""
    res = get_customer(customer_id)
    if res.get("error") or not res["rows"]:
        return {"error": res.get("error", f"customer {customer_id} not found")}
    c = res["rows"][0]
    facts = []
    if c["n_delinquent_months"]:
        facts.append(f"delinquent in {c['n_delinquent_months']} of the last 6 months (worst delay {c['max_delay']} month(s))")
    if c["util_latest"] and c["util_latest"] > 0.8:
        facts.append(f"latest credit utilisation {c['util_latest']:.0%} of the limit")
    return {
        "customer_id": customer_id,
        "risk_segment": c["risk_segment"],
        "risk_proba": round(c["risk_proba"], 3),
        "model_drivers": c["top_risk_factors"],
        "facts": facts,
    }


def propose_intervention(
    customer_id: int,
    action_type: str,
    rationale: str,
    cited_chunk_ids: list[str],
) -> dict[str, Any]:
    """Record a recommended action for human approval. It is NOT executed.

    action_type must be one of EMI_EXTENSION, RESTRUCTURING_REVIEW, COUNSELLING_REFERRAL,
    PAYMENT_REMINDER, NO_ACTION. Every action except NO_ACTION must cite at least one policy
    chunk_id returned by search_policies in this conversation.
    """
    action_type = action_type.upper()
    if action_type not in ACTION_TYPES:
        return {"error": f"action_type must be one of {sorted(ACTION_TYPES)}"}
    if action_type != "NO_ACTION" and not cited_chunk_ids:
        return {"error": "Every recommendation needs at least one policy citation (chunk_id)."}
    store = get_store()
    citations = []
    for cid in cited_chunk_ids:
        ch = store.get(cid)
        if ch is None:
            return {"error": f"unknown chunk_id '{cid}'. Cite only chunk_ids from search_policies."}
        citations.append({"doc": ch.doc_title, "section": ch.section, "page": ch.page, "chunk_id": cid})
    with session_scope() as db:
        if db.scalar(select(Customer.customer_id).where(Customer.customer_id == customer_id)) is None:
            return {"error": f"customer {customer_id} not found"}
        row = Intervention(
            customer_id=customer_id, action_type=action_type, rationale=rationale[:2000],
            citations=citations, status="proposed",
        )
        db.add(row)
        db.flush()
        rid = row.id
    return {
        "intervention_id": rid, "status": "proposed", "requires_human_approval": True,
        "action": ACTION_TYPES[action_type], "citations": citations,
    }


INTERVENTION_TOOLS: list[Any] = [get_risk_factors, propose_intervention]
