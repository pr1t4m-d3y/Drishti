"""OpenTelemetry setup. ADK emits spans for agents, LLM calls and tool calls; we add spans for
retrieval and the HTTP layer, and export to Cloud Trace (cloud) or the console (local).

`TRACE_EXPORTER`: console | otlp (Jaeger / any collector, via OTEL_EXPORTER_OTLP_ENDPOINT) | gcp | none
"""

from __future__ import annotations

import re

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)

from drishti.config import get_settings
from drishti.obs.pii import mask_pii

_configured = False


class PiiMaskingExporter(SpanExporter):
    """Wraps another exporter and masks PII in string attributes before they leave the process."""

    def __init__(self, inner: SpanExporter):
        self._inner = inner

    def export(self, spans):
        for sp in spans:
            attrs = getattr(sp, "_attributes", None)
            if attrs is not None:
                for k, v in list(attrs.items()):
                    if isinstance(v, str):
                        try:
                            attrs[k] = mask_pii(v)
                        except TypeError:  # BoundedAttributes can be immutable
                            pass
        return self._inner.export(spans)

    def shutdown(self) -> None:
        self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)


def setup_tracing(service_name: str = "drishti-api") -> None:
    global _configured
    if _configured:
        return
    kind = get_settings().trace_exporter
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if kind == "console":
        provider.add_span_processor(SimpleSpanProcessor(PiiMaskingExporter(ConsoleSpanExporter())))
    elif kind == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(PiiMaskingExporter(OTLPSpanExporter())))
    elif kind == "gcp":
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

        provider.add_span_processor(BatchSpanProcessor(PiiMaskingExporter(CloudTraceSpanExporter())))
    trace.set_tracer_provider(provider)
    _configured = True


def tracer() -> trace.Tracer:
    return trace.get_tracer("drishti")


def current_trace_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else re.sub(r"-", "", "0" * 32)
