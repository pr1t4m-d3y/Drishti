from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,64}$")
    stream: bool = False


class Citation(BaseModel):
    doc: str | None = None
    section: str | None = None
    paragraph: str | None = None
    page: int | None = None
    chunk_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    trace_id: str
    refused: bool = False
    grounded: bool | None = None
    citations: list[Citation] = []
    verifier_issues: list[str] = []
    metrics: dict


class PredictRequest(BaseModel):
    """Raw monthly card data for one customer. pay_1 is the most recent month."""

    model_config = ConfigDict(extra="forbid")
    limit_bal: float = Field(gt=0)
    sex: int = Field(ge=1, le=2)
    education: int = Field(ge=0, le=6)
    marriage: int = Field(ge=0, le=3)
    age: int = Field(ge=18, le=100)
    pay_1: int = Field(ge=-2, le=9)
    pay_2: int = Field(ge=-2, le=9)
    pay_3: int = Field(ge=-2, le=9)
    pay_4: int = Field(ge=-2, le=9)
    pay_5: int = Field(ge=-2, le=9)
    pay_6: int = Field(ge=-2, le=9)
    bill_amt1: float
    bill_amt2: float
    bill_amt3: float
    bill_amt4: float
    bill_amt5: float
    bill_amt6: float
    pay_amt1: float = Field(ge=0)
    pay_amt2: float = Field(ge=0)
    pay_amt3: float = Field(ge=0)
    pay_amt4: float = Field(ge=0)
    pay_amt5: float = Field(ge=0)
    pay_amt6: float = Field(ge=0)


class PredictResponse(BaseModel):
    risk_proba: float
    risk_segment: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    top_risk_factors: list[dict]


class EarlyWarningItem(BaseModel):
    customer_id: int
    risk_proba: float
    risk_segment: str
    n_delinquent_months: int
    top_risk_factors: list[dict]


class InterventionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    action_type: str
    rationale: str
    citations: list[dict]
    status: str
    created_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=1000)


class ErrorBody(BaseModel):
    code: str
    message: str
    trace_id: str | None = None
