"""Structured JSON logging with PII masking. One JSON object per line (Cloud Logging friendly)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from drishti.obs.pii import mask_pii

_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        try:  # metrics lines are already JSON: embed them as objects, not strings
            payload = json.loads(msg)
            body: dict = {"metrics": payload} if isinstance(payload, dict) else {"message": msg}
        except ValueError:
            body = {"message": mask_pii(msg)}
        out = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "severity": record.levelname,
            "logger": record.name,
            **body,
        }
        if record.exc_info:
            out["exception"] = mask_pii(self.formatException(record.exc_info))
        return json.dumps(out, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    for name in ("drishti", "drishti.metrics", "drishti.api"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.handlers = [handler]
        lg.propagate = False
    _configured = True
