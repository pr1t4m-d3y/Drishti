"""Chat runtime: ADK Runner + persistent sessions + tracing + metrics + guardrails.

`ChatService.chat()` is an async generator that yields progress events (for streaming) and ends
with a `final` event containing the verified answer, citations, trace id and metrics.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from google.adk import Runner
from google.adk.apps import App
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from drishti.agents.guardrails import REFUSALS, check_user_input
from drishti.agents.system import System, build_system
from drishti.agents.verifier import Evidence, finalize, verify
from drishti.config import get_settings
from drishti.db.models import RequestMetric
from drishti.db.session import session_scope
from drishti.obs.metrics import MetricsPlugin, log_metrics
from drishti.obs.pii import mask_pii
from drishti.obs.tracing import current_trace_id, setup_tracing, tracer

APP_NAME = "drishti"


class ChatService:
    def __init__(self, system: System | None = None, session_service: Any = None, strict: bool = True):
        setup_tracing()
        s = get_settings()
        self.system = system or build_system("final")
        self.sessions = session_service or DatabaseSessionService(db_url=s.session_db_url)
        self.metrics = MetricsPlugin()
        self.strict = strict
        app = App(name=APP_NAME, root_agent=self.system.root, plugins=[self.metrics])
        self.runner = Runner(app=app, session_service=self.sessions)

    async def get_or_create_session(self, user_id: str, session_id: str | None) -> str:
        if session_id:
            existing = await self.sessions.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            if existing:
                return session_id
        sid = session_id or uuid.uuid4().hex
        await self.sessions.create_session(app_name=APP_NAME, user_id=user_id, session_id=sid)
        return sid

    async def history(self, user_id: str, session_id: str) -> list[dict]:
        sess = await self.sessions.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        if not sess:
            return []
        out = []
        for ev in sess.events:
            text = "".join(p.text or "" for p in ((ev.content.parts or []) if ev.content else []) if p.text)
            if text and ev.author in ("user", "orchestrator", "baseline_agent"):
                out.append({"role": "user" if ev.author == "user" else "assistant", "text": mask_pii(text)})
        return out

    async def chat(self, user_id: str, message: str, session_id: str | None = None) -> AsyncIterator[dict]:
        with tracer().start_as_current_span("chat.request") as span:
            trace_id = current_trace_id()
            sid = await self.get_or_create_session(user_id, session_id)
            span.set_attribute("session.id", sid)
            span.set_attribute("variant", self.system.variant)
            m = self.metrics.start(trace_id, sid, get_settings().llm_model)

            verdict = check_user_input(message)
            if not verdict.allowed:
                span.set_attribute("guardrail.blocked", verdict.category)
                payload = m.finish()
                payload["guardrail"] = verdict.category
                self._persist(payload)
                yield {"type": "final", "answer": REFUSALS[verdict.category], "refused": True,
                       "category": verdict.category, "citations": [], "trace_id": trace_id,
                       "session_id": sid, "metrics": payload}
                return

            evidence, final_text = Evidence(), ""
            content = types.Content(role="user", parts=[types.Part(text=message)])
            async for ev in self.runner.run_async(user_id=user_id, session_id=sid, new_message=content):
                for fc in ev.get_function_calls():
                    yield {"type": "tool_call", "agent": ev.author, "tool": fc.name}
                if ev.is_final_response() and ev.content and ev.author == self.system.root.name:
                    final_text = "".join(p.text or "" for p in (ev.content.parts or []) if p.text)

            for name, result in m.tool_results:  # collected by the plugin, incl. sub-agent tools
                evidence.add_tool_result(name, result)

            if self.system.use_verifier:
                result = verify(final_text, evidence)
                answer = finalize(result, strict=self.strict)
                issues, citations, grounded = result.issues, result.citations, result.grounded
            else:  # baseline: no verifier, only PII masking
                answer, issues, citations, grounded = mask_pii(final_text), [], [], None

            payload = m.finish()
            payload["grounded"] = grounded
            payload["verifier_issues"] = len(issues)
            self._persist(payload)
            yield {"type": "final", "answer": answer, "refused": False, "citations": citations,
                   "verifier_issues": issues, "grounded": grounded, "trace_id": trace_id,
                   "session_id": sid, "metrics": payload}

    @staticmethod
    def _persist(payload: dict) -> None:
        log_metrics(payload)
        with session_scope() as db:
            db.add(RequestMetric(trace_id=payload["trace_id"], session_id=payload["session_id"], payload=payload))
