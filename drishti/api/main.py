"""FastAPI service: early-warning scoring, customer/intervention endpoints and the /chat copilot."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, select

from drishti.api.auth import Principal, require_admin, require_key
from drishti.api.schemas import (
    ChatRequest,
    ChatResponse,
    DecisionRequest,
    EarlyWarningItem,
    InterventionOut,
    PredictRequest,
    PredictResponse,
)
from drishti.config import get_settings
from drishti.db.models import Customer, Intervention
from drishti.db.session import init_db, session_scope
from drishti.ml.predict import score_frame
from drishti.obs.logging import setup_logging
from drishti.obs.tracing import current_trace_id, setup_tracing

log = logging.getLogger("drishti.api")


def _key_func(request: Request) -> str:
    return request.headers.get("x-api-key") or get_remote_address(request)


limiter = Limiter(key_func=_key_func, default_limits=[get_settings().rate_limit])
_chat = None  # ChatService is built lazily: importing the API must not require cloud credentials.


def chat_service():
    global _chat
    if _chat is None:
        from drishti.agents.runtime import ChatService

        _chat = ChatService()
    return _chat


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    setup_tracing()
    init_db()
    yield


app = FastAPI(title="Drishti", version="0.2.0", lifespan=lifespan)
app.state.limiter = limiter
FastAPIInstrumentor.instrument_app(app, excluded_urls="health")


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, "trace_id": current_trace_id()}}
    )


@app.exception_handler(RateLimitExceeded)
async def _rate(_: Request, exc: RateLimitExceeded):
    return _err(429, "rate_limited", f"Rate limit exceeded: {exc.detail}")


@app.exception_handler(HTTPException)
async def _http(_: Request, exc: HTTPException):
    return _err(exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5])
    return _err(422, "validation_error", msg)


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception):
    log.exception("unhandled error")  # stack trace stays in logs, never in the response
    return _err(500, "internal_error", "Unexpected error")


# ---- health ------------------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    with session_scope() as db:
        n = db.scalar(select(func.count()).select_from(Customer))
    return {"status": "ok", "customers": n, "time": datetime.now(UTC).isoformat(timespec="seconds")}


# ---- early warning / scoring -------------------------------------------------------------------

@app.post("/predict", response_model=PredictResponse)
@limiter.limit(get_settings().rate_limit)
def predict(request: Request, body: PredictRequest, _: Principal = Depends(require_key)):
    df = score_frame(pd.DataFrame([body.model_dump()]))
    row = df.iloc[0]
    return PredictResponse(
        risk_proba=round(float(row["risk_proba"]), 4),
        risk_segment=row["risk_segment"],
        top_risk_factors=row["top_risk_factors"],
    )


@app.get("/early-warning", response_model=list[EarlyWarningItem])
def early_warning(
    segment: str = Query("CRITICAL", pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$"),
    limit: int = Query(20, ge=1, le=200),
    _: Principal = Depends(require_key),
):
    """Customers currently in a risk segment, highest probability first."""
    with session_scope() as db:
        rows = db.scalars(
            select(Customer).where(Customer.risk_segment == segment).order_by(Customer.risk_proba.desc()).limit(limit)
        ).all()
        return [
            EarlyWarningItem(
                customer_id=c.customer_id, risk_proba=round(c.risk_proba, 4), risk_segment=c.risk_segment,
                n_delinquent_months=c.n_delinquent_months, top_risk_factors=c.top_risk_factors,
            )
            for c in rows
        ]


@app.get("/api/stats")
def stats(_: Principal = Depends(require_key)) -> dict:
    with session_scope() as db:
        rows = db.execute(
            select(Customer.risk_segment, func.count(), func.avg(Customer.risk_proba)).group_by(Customer.risk_segment)
        ).all()
    return {"segments": {seg: {"customers": n, "avg_risk": round(float(avg), 4)} for seg, n, avg in rows},
            "total": sum(n for _, n, _ in rows)}


@app.get("/api/customers/{customer_id}")
def customer(customer_id: int, _: Principal = Depends(require_key)) -> dict:
    with session_scope() as db:
        c = db.get(Customer, customer_id)
        if c is None:
            raise HTTPException(404, "customer not found")
        d = {k: v for k, v in c.__dict__.items() if not k.startswith("_") and k != "default_label"}
        d["scored_at"] = d["scored_at"].isoformat() if d.get("scored_at") else None
        return d


# ---- interventions: human-in-the-loop ----------------------------------------------------------

@app.get("/interventions", response_model=list[InterventionOut])
def list_interventions(status: str | None = Query(None, pattern="^(proposed|approved|rejected)$"),
                       _: Principal = Depends(require_key)):
    with session_scope() as db:
        q = select(Intervention).order_by(Intervention.created_at.desc()).limit(100)
        if status:
            q = q.where(Intervention.status == status)
        return [InterventionOut.model_validate(r) for r in db.scalars(q)]


@app.post("/interventions/{intervention_id}/decision", response_model=InterventionOut)
def decide(intervention_id: int, body: DecisionRequest, who: Principal = Depends(require_key)):
    """The only way a recommendation becomes 'approved'. The decision-maker is the authenticated user."""
    with session_scope() as db:
        row = db.get(Intervention, intervention_id)
        if row is None:
            raise HTTPException(404, "intervention not found")
        if row.status != "proposed":
            raise HTTPException(409, f"already {row.status}")
        row.status, row.decided_by, row.decided_at, row.decision_note = (
            body.decision, who.name, datetime.now(UTC), body.note)
        db.flush()
        return InterventionOut.model_validate(row)


# ---- copilot -----------------------------------------------------------------------------------

@app.post("/chat")
@limiter.limit(get_settings().rate_limit)
async def chat(request: Request, body: ChatRequest, who: Principal = Depends(require_key)):
    svc = chat_service()

    if body.stream:
        async def sse():
            async for ev in svc.chat(who.name, body.message, body.session_id):
                yield f"event: {ev['type']}\ndata: {json.dumps(ev, default=str)}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    final = None
    async for ev in svc.chat(who.name, body.message, body.session_id):
        if ev["type"] == "final":
            final = ev
    assert final is not None
    return ChatResponse(**{k: final.get(k) for k in ChatResponse.model_fields if k in final})


@app.get("/sessions/{session_id}")
async def get_session(session_id: str, who: Principal = Depends(require_key)) -> dict:
    hist = await chat_service().history(who.name, session_id)
    if not hist:
        raise HTTPException(404, "session not found")
    return {"session_id": session_id, "messages": hist}


@app.get("/admin/metrics")
def metrics_summary(_: Principal = Depends(require_admin)) -> dict:
    """p50/p95 latency, tokens/sec and cost across recorded requests."""
    from drishti.db.models import RequestMetric
    from drishti.obs.metrics import percentile

    with session_scope() as db:
        payloads = [r.payload for r in db.scalars(select(RequestMetric))]
    lat = [p["latency_s"] for p in payloads if p.get("latency_s") is not None]
    tps = [p["tokens_per_sec"] for p in payloads if p.get("tokens_per_sec")]
    cost = [p["cost_usd"] for p in payloads if p.get("cost_usd") is not None]
    return {
        "requests": len(payloads),
        "latency_p50_s": percentile(lat, 50), "latency_p95_s": percentile(lat, 95),
        "tokens_per_sec_p50": percentile(tps, 50),
        "cost_usd_mean": round(sum(cost) / len(cost), 6) if cost else None,
    }
