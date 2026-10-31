"""Graph nodes. Each is thin: call a service, return a partial state update.

Customer-facing messages are not written here; the runtime stores `reply` after the run, so a
node never sends anything twice (D-010).
"""

import asyncio
from dataclasses import asdict
from typing import Any

from langgraph.types import interrupt

from app.agent.deps import Deps
from app.agent.state import AgentState
from app.schemas.decision import DecisionAdapter, Edits
from app.schemas.extraction import Extraction
from app.schemas.pricing import Discount, PricingInput
from app.services.clarify import clarify_message
from app.services.guardrail import check as guardrail_check
from app.services.pdf import render_pdf as render_quote_pdf
from app.services.pricing import PricingError, price_quote
from app.services.states import state_code
from app.services.validator import ValidationResult, validate

# Outcomes after which the next message starts a new request rather than continuing one.
_CONTINUE_INQUIRY = ("needs_clarification", "replied")

REPLY_OTHER = (
    "Thanks for your message! For a quote, tell us the product, how many you need, and details "
    "like sizes, colours or print type."
)
REPLY_CANCELLED = "Done, we've cancelled your quote {number}. Message us any time for a new one."
REPLY_NOTHING_TO_CANCEL = "There's no open quote to cancel. Message us any time for a new one."
REPLY_PREPARING = (
    "Thanks! We have everything we need. Your quote {number} is being prepared and will be "
    "sent after a quick review."
)
REPLY_APPROVED = "Your quote {number} is ready."
REPLY_REFUSED = (
    "Sorry, I can only help with quotes for our products. Tell us what you need, how many, and "
    "details like sizes or finish, and we'll prepare a quote."
)
REPLY_REJECTED = (
    "Sorry, we can't take on this order right now (quote {number}). We'll be in touch if that "
    "changes."
)


class Nodes:
    def __init__(self, deps: Deps) -> None:
        self.deps = deps

    async def ingest(self, state: AgentState) -> dict[str, Any]:
        """Start a turn: reset per-turn fields and decide whether this continues a request."""
        customer = state.get("customer") or {}
        await self.deps.repo.ensure_conversation(  # idempotent upsert
            state["conversation_id"],
            name=customer.get("name", ""),
            phone=customer.get("phone", ""),
            state=state_code(customer.get("state")),
        )
        previous = state.get("pending_inquiry") or []
        keep = previous if state.get("outcome") in _CONTINUE_INQUIRY else []
        return {
            "pending_inquiry": [*keep, state["raw_query"]],
            "guardrail": {},
            "intent": "",
            "extraction": {},
            "validation": {},
            "pricing_inputs": [],
            "discount": None,
            "quote_id": None,
            "revision": 0,
            "line_items": [],
            "totals": {},
            "flags": [],
            "pdf_path": None,
            "decision": None,
            "edit_errors": [],
            "reply": "",
        }

    async def guardrail(self, state: AgentState) -> dict[str, Any]:
        verdict = await guardrail_check(state["raw_query"], self.deps.classify_risk)
        return {"guardrail": asdict(verdict)}

    async def reject_draft(self, state: AgentState) -> dict[str, Any]:
        """Polite refusal for injection/abuse. Nothing is extracted or priced (D-015)."""
        return {"reply": REPLY_REFUSED, "outcome": "rejected_input", "pending_inquiry": []}

    async def intent(self, state: AgentState) -> dict[str, Any]:
        result = await self.deps.classify_intent(state["raw_query"])
        return {"intent": result.intent}

    async def extract(self, state: AgentState) -> dict[str, Any]:
        text = "\n".join(state["pending_inquiry"])
        extraction = await self.deps.extract(text)
        return {"extraction": extraction.model_dump(mode="json")}

    async def validate(self, state: AgentState) -> dict[str, Any]:
        result = validate(Extraction.model_validate(state["extraction"]), self.deps.catalog)
        update: dict[str, Any] = {"validation": result.model_dump(mode="json")}
        if result.complete:
            update["pricing_inputs"] = [p.model_dump() for p in result.pricing_inputs()]
        return update

    async def clarify_draft(self, state: AgentState) -> dict[str, Any]:
        result = ValidationResult.model_validate(state["validation"])
        return {
            "reply": clarify_message(result, self.deps.catalog),
            "outcome": "needs_clarification",
        }

    async def reply_draft(self, state: AgentState) -> dict[str, Any]:
        return {"reply": REPLY_OTHER, "outcome": "replied", "pending_inquiry": []}

    async def cancel_handler(self, state: AgentState) -> dict[str, Any]:
        repo = self.deps.repo
        quote = await repo.latest_open_quote(state["conversation_id"])
        if quote is None:
            return {"reply": REPLY_NOTHING_TO_CANCEL, "outcome": "cancelled", "pending_inquiry": []}
        await repo.set_status(quote.id, "cancelled", event={"by": "customer"})
        return {
            "reply": REPLY_CANCELLED.format(number=quote.number),
            "outcome": "cancelled",
            "quote_id": quote.id,
            "pending_inquiry": [],
        }

    def _customer_state(self, state: AgentState) -> str | None:
        customer = state.get("customer") or {}
        return state_code(customer.get("state")) or state_code(
            (state.get("extraction") or {}).get("customer_state")
        )

    async def price(self, state: AgentState) -> dict[str, Any]:
        repo = self.deps.repo
        customer_state = self._customer_state(state)
        quote_id = state.get("quote_id")
        if not quote_id:
            quote = await repo.create_quote(
                state["conversation_id"],
                raw_query="\n".join(state["pending_inquiry"]),
                extraction=state["extraction"],
                validation=state["validation"],
                customer_state=customer_state,
            )
            quote_id = quote.id
        discount = Discount.model_validate(state["discount"]) if state.get("discount") else None
        priced = price_quote(
            [PricingInput.model_validate(p) for p in state["pricing_inputs"]],
            catalog=self.deps.catalog,
            business_state=self.deps.settings.business_state,
            customer_state=customer_state,
            discount=discount,
        )
        revision = (state.get("revision") or 0) + 1
        flags = [*priced.flags, *(state.get("guardrail") or {}).get("flags", [])]
        await repo.save_revision(
            quote_id, revision, priced, discount=state.get("discount"), flags=flags
        )
        return {
            "quote_id": quote_id,
            "revision": revision,
            "line_items": [line.model_dump() for line in priced.lines],
            "totals": priced.totals.model_dump(),
            "flags": flags,
            "pending_inquiry": [],
            "edit_errors": [],
        }

    async def _render(self, quote_id: str, *, draft: bool) -> str:
        repo = self.deps.repo
        quote = await repo.get_quote(quote_id)
        items = await repo.get_items(quote_id)
        conversation = await repo.get_conversation(quote.conversation_id)
        rel = await asyncio.to_thread(
            render_quote_pdf, quote, items, conversation, self.deps.settings, draft=draft
        )
        return rel.as_posix()

    async def render_pdf(self, state: AgentState) -> dict[str, Any]:
        """Draft PDF for the owner's review; the final one is rendered on approval."""
        return {"pdf_path": await self._render(state["quote_id"], draft=True)}

    # --- human in the loop (Phase 05) -------------------------------------------------------------

    async def submit_for_review(self, state: AgentState) -> dict[str, Any]:
        """Put the quote in the owner's inbox. Runs before the pause, so the resume replay of
        `hitl_pause` never repeats it (D-010)."""
        quote = await self.deps.repo.set_status(
            state["quote_id"],
            "awaiting_approval",
            event={"revision": state["revision"]},
            pdf_path=state.get("pdf_path"),
        )
        update: dict[str, Any] = {"outcome": "awaiting_approval"}
        if state["revision"] == 1:  # tell the customer once, not after every owner edit
            update["reply"] = REPLY_PREPARING.format(number=quote.number)
        return update

    async def hitl_pause(self, state: AgentState) -> dict[str, Any]:
        # D-010: nothing above interrupt() may have side effects; this node re-runs on resume.
        decision = interrupt(
            {
                "quote_id": state["quote_id"],
                "conversation_id": state["conversation_id"],
                "revision": state["revision"],
                "line_items": state["line_items"],
                "totals": state["totals"],
                "flags": state.get("flags", []),
                "pdf_path": state.get("pdf_path"),
                "edit_errors": state.get("edit_errors", []),
            }
        )
        parsed = DecisionAdapter.validate_python(decision)
        return {"decision": parsed.model_dump(mode="json"), "reply": "", "edit_errors": []}

    async def apply_edits(self, state: AgentState) -> dict[str, Any]:
        """Turn the owner's structured edits into new pricing inputs, or explain why not."""
        edits = Edits.model_validate(state["decision"]["edits"])
        current = {p["sku"]: p for p in state["pricing_inputs"]}
        inputs = state["pricing_inputs"]
        if edits.items is not None:
            inputs = [
                PricingInput(
                    sku=e.sku,
                    quantity=e.quantity,
                    specs=e.specs
                    if e.specs is not None
                    else current.get(e.sku, {}).get("specs", {}),
                ).model_dump()
                for e in edits.items
            ]
        discount = state.get("discount")
        if edits.remove_discount:
            discount = None
        elif edits.discount is not None:
            discount = edits.discount.model_dump()

        try:  # dry run: catches unknown SKUs, MOQ, bad options, oversized discounts
            price_quote(
                [PricingInput.model_validate(p) for p in inputs],
                catalog=self.deps.catalog,
                business_state=self.deps.settings.business_state,
                customer_state=self._customer_state(state),
                discount=Discount.model_validate(discount) if discount else None,
            )
        except (PricingError, ValueError) as exc:
            await self.deps.repo.add_event(state["quote_id"], "edit_rejected", {"error": str(exc)})
            return {"edit_errors": [str(exc)]}

        await self.deps.repo.add_event(
            state["quote_id"], "edited", {"from_revision": state["revision"], **edits.model_dump()}
        )
        return {"pricing_inputs": inputs, "discount": discount, "edit_errors": []}

    async def mark_rejected(self, state: AgentState) -> dict[str, Any]:
        reason = state["decision"]["reason"]
        quote = await self.deps.repo.set_status(
            state["quote_id"], "rejected", event={"reason": reason}, rejection_reason=reason
        )
        return {"reply": REPLY_REJECTED.format(number=quote.number), "outcome": "rejected"}

    async def dispatch(self, state: AgentState) -> dict[str, Any]:
        # Phase 11 adds sending the PDF link and the follow-up timer.
        final_pdf = await self._render(state["quote_id"], draft=False)
        quote = await self.deps.repo.set_status(state["quote_id"], "approved", pdf_path=final_pdf)
        return {
            "reply": REPLY_APPROVED.format(number=quote.number),
            "outcome": "approved",
            "pdf_path": final_pdf,
        }


def route_decision(state: AgentState) -> str:
    return state["decision"]["action"]


def route_edits(state: AgentState) -> str:
    return "invalid" if state.get("edit_errors") else "ok"


def route_guardrail(state: AgentState) -> str:
    return "flagged" if state["guardrail"].get("flagged") else "ok"


def route_intent(state: AgentState) -> str:
    return state["intent"] if state["intent"] in ("new_quote", "cancel") else "other"


def route_validation(state: AgentState) -> str:
    return "complete" if state["validation"].get("complete") else "incomplete"
