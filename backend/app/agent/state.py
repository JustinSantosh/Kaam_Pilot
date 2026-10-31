"""Graph state. Values are plain JSON-able dicts/lists so checkpoints stay portable."""

from typing import Any, Literal, TypedDict

Outcome = Literal[
    "needs_clarification",
    "replied",
    "rejected_input",
    "cancelled",
    "awaiting_approval",
    "approved",
    "rejected",
]


class AgentState(TypedDict, total=False):
    conversation_id: str
    customer: dict[str, Any]  # {name, phone, state}
    raw_query: str  # this turn's message (transcribed if voice)
    pending_inquiry: list[str]  # customer messages of the request still being clarified

    guardrail: dict[str, Any]  # {flagged, risk, reason}
    intent: str
    extraction: dict[str, Any]
    validation: dict[str, Any]
    pricing_inputs: list[dict[str, Any]]  # what `price` prices; edits change this (D-009)
    discount: dict[str, Any] | None

    quote_id: str | None
    revision: int
    line_items: list[dict[str, Any]]
    totals: dict[str, Any]
    flags: list[str]
    pdf_path: str | None

    decision: dict[str, Any] | None
    edit_errors: list[str]

    reply: str  # message for the customer from this turn
    outcome: Outcome
