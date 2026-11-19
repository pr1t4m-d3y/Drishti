"""Deterministic guardrails (the verifier agent adds an LLM check on top of these).

1. `check_user_input`     : refuse jailbreaks, PII-extraction, destructive or out-of-scope asks.
2. `scan_untrusted_text`  : detect prompt injection hidden in retrieved documents / tool output.
3. `verify_citations`     : every cited chunk id must exist in the evidence retrieved this turn.
4. `mask_output`          : PII masking on the final answer.

Pattern lists are deliberately simple and auditable. They are a first line of defence, not a
claim of completeness; the adversarial section of the golden set measures how well they work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from drishti.obs.pii import mask_pii

_INJECTION = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above|system) ",
    r"you are now (?!able)",
    r"(reveal|show|print|repeat) (your |the )?(system|hidden|developer)( (system|hidden|developer))? (prompt|instructions|message)",
    r"act as (an? )?(unrestricted|jailbroken|dan)\b",
    r"\bdeveloper mode\b",
    r"\bjailbreak\b",
    r"(?:^|\n)\s*(system|assistant)\s*:",
    r"<\s*/?\s*(system|instructions?)\s*>",
    r"do not (tell|inform|mention to) the (user|admin|analyst)",
    r"(execute|run|call) (the )?(tool|function|query) .{0,40}(delete|drop|update|insert|truncate)",
]
_PII_EXTRACTION = [
    r"(list|give|show|dump|export|send) (me )?(all|every|the full) .{0,30}(customers?|records?|names?|accounts?)",
    r"\b(aadhaar|pan number|card number|cvv|password|otp|api key|secret)\b",
    r"(email|phone|address|mobile) (of|for) (customer|client|everyone|all)",
]
_DESTRUCTIVE = [
    r"\b(delete|drop|truncate|alter|update|insert)\b.{0,40}\b(table|customers?|records?|database|interventions?)\b",
    r"\b(approve|execute|apply|process|send)\b.{0,40}\b(restructur\w*|extension|waiver|write.?off)\b.{0,40}\b(now|immediately|automatically)\b",
    r"\bwrite.?off\b",
]
_OUT_OF_SCOPE = [
    r"\b(stock|crypto|bitcoin|forex|lottery|horoscope|recipe|weather|movie)\b",
    r"\b(write|compose) (me )?(a |an )?(poem|song|story|essay|joke|code|script)\b",
    r"\b(medical|legal) advice\b",
]


@dataclass
class Verdict:
    allowed: bool
    category: str = "ok"  # ok | jailbreak | pii_extraction | destructive | out_of_scope
    reason: str = ""
    flags: list[str] = field(default_factory=list)


def _first(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return p
    return None


def check_user_input(text: str) -> Verdict:
    if _first(_INJECTION, text):
        return Verdict(False, "jailbreak", "Instruction-override or prompt-extraction attempt.")
    if _first(_DESTRUCTIVE, text):
        return Verdict(False, "destructive", "This assistant is read-only and never executes actions.")
    if _first(_PII_EXTRACTION, text):
        return Verdict(False, "pii_extraction", "Bulk or sensitive personal-data requests are not permitted.")
    if _first(_OUT_OF_SCOPE, text):
        return Verdict(False, "out_of_scope", "Only credit-risk, lending-policy and intervention questions are supported.")
    return Verdict(True)


def scan_untrusted_text(text: str) -> tuple[str, list[str]]:
    """Neutralise injected instructions inside retrieved text. Returns (safe_text, flags)."""
    flags: list[str] = []
    safe = text
    for p in _INJECTION:
        if re.search(p, safe, re.IGNORECASE):
            flags.append(p)
            safe = re.sub(p, "[REMOVED: suspected prompt injection]", safe, flags=re.IGNORECASE)
    return safe, flags


def verify_citations(cited_chunk_ids: list[str], evidence_chunk_ids: set[str]) -> tuple[bool, list[str]]:
    missing = [c for c in cited_chunk_ids if c not in evidence_chunk_ids]
    return (not missing), missing


def mask_output(text: str) -> str:
    return mask_pii(text)


REFUSALS = {
    "jailbreak": "I can't follow instructions that override my rules or ask me to reveal internal prompts.",
    "destructive": "I'm read-only: I can recommend actions for human approval, but I never execute or modify data.",
    "pii_extraction": "I can't provide bulk or sensitive personal data. I can answer aggregate questions or look up a specific customer's risk profile.",
    "out_of_scope": "That's outside what I can help with. I handle credit-risk data, lending policy and intervention recommendations.",
}
