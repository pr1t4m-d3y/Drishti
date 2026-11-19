"""Rubric-based LLM-as-judge (Gemini). Needs cloud credentials; skipped in offline mode."""

from __future__ import annotations

import json
import re
from pathlib import Path

from drishti.config import get_settings

RUBRIC = (Path(__file__).parent / "rubric.md").read_text()
CRITERIA = ("correctness", "groundedness", "completeness", "safety")


def judge(question: str, answer: str, evidence: str, reference: str = "") -> dict | None:
    from google import genai
    from google.genai import types

    prompt = (
        f"{RUBRIC}\n\nQUESTION:\n{question}\n\nREFERENCE (may be empty):\n{reference}\n\n"
        f"EVIDENCE:\n{evidence[:6000]}\n\nANSWER:\n{answer}\n\nReturn only the JSON object."
    )
    client = genai.Client()
    resp = client.models.generate_content(
        model=get_settings().judge_model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    try:
        data = json.loads(re.sub(r"^```json|```$", "", (resp.text or "").strip()))
        return {k: int(data[k]) for k in CRITERIA} | {"reason": str(data.get("reason", ""))[:300]}
    except (ValueError, KeyError, TypeError):
        return None
