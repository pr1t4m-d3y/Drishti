"""Per-request LLM metrics, collected by an ADK plugin and logged as one structured JSON line.

Tracked per request: input/output tokens, tokens/sec, latency, cost, agent steps, tool calls,
retrieval calls. Percentiles (p50/p95) are computed over many requests by `percentile()`.
"""

from __future__ import annotations

import json
import logging
import math
import time
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

from google.adk.plugins import BasePlugin

from drishti.config import get_settings

log = logging.getLogger("drishti.metrics")


@lru_cache
def pricing_table() -> dict:
    return json.loads(get_settings().pricing_path.read_text())


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Cost from the dated pricing table. None if the model is not priced (never guessed)."""
    price = pricing_table()["models"].get(model.split("/")[-1])
    if not price:
        return None
    return round((input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000, 6)


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile (p in 0..100)."""
    if not values:
        return None
    s = sorted(values)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


@dataclass
class RequestMetrics:
    trace_id: str = ""
    session_id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    retrieval_calls: int = 0
    agents_invoked: list[str] = field(default_factory=list)
    llm_time_s: float = 0.0
    latency_s: float = 0.0
    first_token_s: float | None = None
    tools_used: list[str] = field(default_factory=list)
    # Raw tool outputs for the verifier. Never logged or persisted (excluded in finish()).
    _tool_results: list[tuple[str, Any]] = field(default_factory=list, repr=False)
    _t0: float = field(default_factory=time.perf_counter, repr=False)

    def finish(self) -> dict[str, Any]:
        self.latency_s = round(time.perf_counter() - self._t0, 3)
        d = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        d["agent_steps"] = self.llm_calls + self.tool_calls
        d["tokens_per_sec"] = (
            round(self.output_tokens / self.llm_time_s, 2) if self.llm_time_s > 0 and self.output_tokens else None
        )
        d["cost_usd"] = cost_usd(self.model, self.input_tokens, self.output_tokens)
        d["pricing_as_of"] = pricing_table()["as_of"]
        d["agents_invoked"] = sorted(set(self.agents_invoked))
        d["tools_used"] = list(self.tools_used)
        return d

    @property
    def tool_results(self) -> list[tuple[str, Any]]:
        return self._tool_results


# AgentTool runs sub-agents in child sessions, so we cannot key by session id. A ContextVar set by
# the chat service is inherited by those child tasks and is safe under concurrent requests.
CURRENT: ContextVar[RequestMetrics | None] = ContextVar("drishti_request_metrics", default=None)


class MetricsPlugin(BasePlugin):
    """Attach to the Runner. One `RequestMetrics` per invocation, keyed by invocation id."""

    def __init__(self) -> None:
        super().__init__(name="drishti_metrics")
        self._call_start: dict[str, float] = {}

    @staticmethod
    def start(trace_id: str, session_id: str, model: str) -> RequestMetrics:
        m = RequestMetrics(trace_id=trace_id, session_id=session_id, model=model)
        CURRENT.set(m)
        return m

    @staticmethod
    def _m(_ctx: Any = None) -> RequestMetrics | None:
        return CURRENT.get()

    async def before_model_callback(self, *, callback_context, llm_request):
        self._call_start[callback_context.invocation_id] = time.perf_counter()
        m = self._m(callback_context)
        if m:
            m.agents_invoked.append(callback_context.agent_name)

    async def after_model_callback(self, *, callback_context, llm_response):
        m = self._m(callback_context)
        t0 = self._call_start.pop(callback_context.invocation_id, None)
        if not m:
            return
        m.llm_calls += 1
        if t0 is not None:
            m.llm_time_s += time.perf_counter() - t0
        u = llm_response.usage_metadata
        if u:
            m.input_tokens += u.prompt_token_count or 0
            m.output_tokens += (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0)

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        m = self._m(tool_context)
        if m:
            m.tool_calls += 1
            m.tools_used.append(tool.name)
            m._tool_results.append((tool.name, result))
            if tool.name == "search_policies":
                m.retrieval_calls += 1


def log_metrics(payload: dict) -> None:
    """One JSON line per request. Contains no user text, so it is PII-free by construction."""
    log.info(json.dumps(payload, default=str))
