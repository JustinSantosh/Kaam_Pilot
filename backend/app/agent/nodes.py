"""Graph nodes. Each is thin: call a service, return a partial state update.

Customer-facing messages are not written here; the runtime stores `reply` after the run, so a
node never sends anything twice (D-010).
"""

from typing import Any

from app.agent.deps import Deps
from app.agent.state import AgentState
from app.schemas.extraction import Extraction
from app.schemas.pricing import Discount, PricingInput
from app.services.clarify import clarify_message
from app.services.pricing import price_quote
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
        return {"guardrail": {"flagged": False, "risk": "none", "reason": ""}}

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
        await repo.save_revision(quote_id, revision, priced, discount=state.get("discount"))
        return {
            "quote_id": quote_id,
            "revision": revision,
            "line_items": [line.model_dump() for line in priced.lines],
            "totals": priced.totals.model_dump(),
            "flags": priced.flags,
            "pending_inquiry": [],
            "edit_errors": [],
        }

    async def render_pdf(self, state: AgentState) -> dict[str, Any]:
        # Phase 06 replaces this stub with real rendering.
        return {"pdf_path": None}


def route_guardrail(state: AgentState) -> str:
    return "flagged" if state["guardrail"].get("flagged") else "ok"


def route_intent(state: AgentState) -> str:
    return state["intent"] if state["intent"] in ("new_quote", "cancel") else "other"


def route_validation(state: AgentState) -> str:
    return "complete" if state["validation"].get("complete") else "incomplete"
