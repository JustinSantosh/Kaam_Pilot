"""Input guardrail: cheap rules first, then an optional LLM risk check (D-015).

This is the *second* line of defence. The first is architectural: the LLM has no field that can
carry a price (D-002/D-003) and a human approves every quote (D-001). So the guardrail can be
simple, and it fails open: if the risk check errors, the message continues and the architecture
still holds.
"""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.schemas.extraction import RiskResult

INJECTION_PATTERNS = [
    r"\bignore\b.{0,30}\b(previous|prior|above|earlier|all)\b.{0,20}\b(instructions?|rules?|prompts?)\b",
    r"\b(system|hidden|initial)\s+prompt\b",
    r"\b(admin|developer|god|debug)\s+mode\b",
    r"\byou\s+are\s+now\b",
    r"\b(reveal|show|print|repeat)\b.{0,20}\b(your|the)\b.{0,10}\b(instructions?|prompt|rules)\b",
    r"\bjailbreak\b",
    r"\bdisregard\b.{0,30}\b(instructions?|rules?)\b",
    r"<\s*/?\s*(inquiry|system)\s*>",
]
MONEY_OVERRIDE_PATTERNS = [
    r"\b(price|rate|cost|total)\b.{0,40}\b(to|=|as|at)\s*(rs\.?|₹|inr)?\s*(0|zero|free|1)\b",
    r"\b(100|hundred)\s*%\s*(discount|off)\b",
    r"\bfree\s+of\s+cost\b",
    r"\b(set|change|make)\b.{0,15}\b(price|rate|total)\b",
    r"\b(9\d|[5-8]\d)\s*%\s*(discount|off)\b",
]
FLAG_MONEY_OVERRIDE = "guardrail_money_override"

_INJECTION = [re.compile(p, re.I) for p in INJECTION_PATTERNS]
_MONEY = [re.compile(p, re.I) for p in MONEY_OVERRIDE_PATTERNS]

RiskCheck = Callable[[str], Awaitable[RiskResult]]


@dataclass
class GuardrailVerdict:
    flagged: bool  # True → polite refusal, no quote
    risk: str  # none | injection | abuse | off_topic
    reason: str
    flags: list[str] = field(default_factory=list)  # carried onto the quote for the owner
    source: str = "rules"  # rules | llm | fail_open


def rule_check(text: str) -> GuardrailVerdict:
    for pattern in _INJECTION:
        if pattern.search(text):
            return GuardrailVerdict(True, "injection", f"matched rule: {pattern.pattern[:40]}")
    flags = [FLAG_MONEY_OVERRIDE] if any(p.search(text) for p in _MONEY) else []
    return GuardrailVerdict(False, "none", "", flags)


async def check(text: str, risk_check: RiskCheck | None) -> GuardrailVerdict:
    verdict = rule_check(text)
    if verdict.flagged or risk_check is None:
        return verdict
    try:
        result = await risk_check(text)
    except Exception as exc:  # fail open: the architecture is the real defence (D-015)
        verdict.source = "fail_open"
        verdict.reason = f"risk check unavailable: {type(exc).__name__}"
        return verdict
    if result.risk in ("injection", "abuse"):
        return GuardrailVerdict(True, result.risk, result.reason, verdict.flags, "llm")
    verdict.risk, verdict.reason, verdict.source = result.risk, result.reason, "llm"
    return verdict
