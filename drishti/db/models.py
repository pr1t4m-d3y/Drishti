"""Relational schema (SQLAlchemy 2.0). Works on PostgreSQL and SQLite."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    """One card-holder. `default_label` is ground truth for evaluation only: agents never read it."""

    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    limit_bal: Mapped[float] = mapped_column(Float)
    sex: Mapped[int] = mapped_column(Integer)
    education: Mapped[int] = mapped_column(Integer)
    marriage: Mapped[int] = mapped_column(Integer)
    age: Mapped[int] = mapped_column(Integer)
    pay_1: Mapped[int] = mapped_column(Integer)
    pay_2: Mapped[int] = mapped_column(Integer)
    pay_3: Mapped[int] = mapped_column(Integer)
    pay_4: Mapped[int] = mapped_column(Integer)
    pay_5: Mapped[int] = mapped_column(Integer)
    pay_6: Mapped[int] = mapped_column(Integer)
    bill_amt1: Mapped[float] = mapped_column(Float)
    bill_amt2: Mapped[float] = mapped_column(Float)
    bill_amt3: Mapped[float] = mapped_column(Float)
    bill_amt4: Mapped[float] = mapped_column(Float)
    bill_amt5: Mapped[float] = mapped_column(Float)
    bill_amt6: Mapped[float] = mapped_column(Float)
    pay_amt1: Mapped[float] = mapped_column(Float)
    pay_amt2: Mapped[float] = mapped_column(Float)
    pay_amt3: Mapped[float] = mapped_column(Float)
    pay_amt4: Mapped[float] = mapped_column(Float)
    pay_amt5: Mapped[float] = mapped_column(Float)
    pay_amt6: Mapped[float] = mapped_column(Float)
    # derived
    n_delinquent_months: Mapped[int] = mapped_column(Integer)
    max_delay: Mapped[int] = mapped_column(Integer)
    util_latest: Mapped[float] = mapped_column(Float)
    # model output
    risk_proba: Mapped[float] = mapped_column(Float, index=True)
    risk_segment: Mapped[str] = mapped_column(String(16), index=True)
    top_risk_factors: Mapped[list] = mapped_column(JSON, default=list)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # evaluation only
    default_label: Mapped[int] = mapped_column(Integer)


class Intervention(Base):
    """A *recommendation* awaiting human approval. The system never executes anything."""

    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    action_type: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)  # [{doc, section, page, chunk_id}]
    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    proposed_by: Mapped[str] = mapped_column(String(64), default="intervention_agent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApiKey(Base):
    """API keys are stored only as salted SHA-256 hashes."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16), default="analyst")  # analyst | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    revoked: Mapped[int] = mapped_column(Integer, default=0)


class RequestMetric(Base):
    """One row per /chat request: tokens, latency, cost, steps. PII-free by construction."""

    __tablename__ = "request_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(32), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    payload: Mapped[dict] = mapped_column(JSON)


Index("ix_customers_seg_proba", Customer.risk_segment, Customer.risk_proba)
