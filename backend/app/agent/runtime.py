"""Runs the graph for the API: one customer message or one owner decision at a time.

- Stores the customer's message and the business reply in the records DB (D-007).
- Never starts a new run while a quote on that conversation is waiting for the owner; the
  customer's message becomes a note on the pending quote instead (D-008).
- Serialises work per conversation with an asyncio lock (single process, D-011).
"""

import asyncio
import re
from collections import defaultdict
from typing import Any, Literal

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel

from app.db.repo import NotFoundError, Repo
from app.schemas.decision import Approve, Edit, Reject
from app.services.followups import FollowupService

TurnStatus = Literal["awaiting_approval", "needs_clarification", "completed", "rejected", "busy"]

REPLY_BUSY = (
    "Your quote is being reviewed right now. We've added your message to it and will reply soon."
)
REPLY_ACCEPTED = (
    "Thank you! Your order for quote {number} is confirmed. We'll contact you shortly about the "
    "advance and delivery."
)
# A bare confirmation only; "yes but make it 60" is a change request and goes to the graph.
ACCEPT = re.compile(
    r"^\s*(yes|y|haan|haa|ha|han|ji haan|confirm(ed)?|ok(ay)?|done|accepted?)"
    r"(\s+(please|pls|ji|bhaiya|confirm(ed)?|order|go ahead))*\s*[.!]*\s*$",
    re.I,
)


class QuoteNotPendingError(RuntimeError):
    pass


class StaleRevisionError(RuntimeError):
    pass


class TurnResult(BaseModel):
    status: TurnStatus
    reply: str
    quote_id: str | None = None
    conversation_id: str


def _config(conversation_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": conversation_id}}


class Runtime:
    def __init__(
        self, graph: CompiledStateGraph, repo: Repo, followups: FollowupService | None = None
    ) -> None:
        self.graph = graph
        self.repo = repo
        self.followups = followups
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def pending(self, conversation_id: str) -> dict[str, Any] | None:
        """The interrupt payload if this conversation is paused at the approval step."""
        snapshot = await self.graph.aget_state(_config(conversation_id))
        for task in snapshot.tasks:
            for intr in task.interrupts:
                return intr.value
        return None

    async def handle_message(
        self,
        conversation_id: str,
        text: str,
        *,
        customer: dict[str, Any] | None = None,
        kind: str = "text",
    ) -> TurnResult:
        customer = customer or {}
        async with self._locks[conversation_id]:
            await self.repo.ensure_conversation(
                conversation_id, name=customer.get("name", ""), phone=customer.get("phone", "")
            )
            await self.repo.add_message(conversation_id, "customer", text, kind=kind)

            waiting = await self.pending(conversation_id)
            if waiting is not None:
                quote_id = waiting["quote_id"]
                await self.repo.add_event(quote_id, "customer_note", {"text": text})
                await self.repo.add_message(
                    conversation_id, "business", REPLY_BUSY, quote_id=quote_id
                )
                return TurnResult(
                    status="busy",
                    reply=REPLY_BUSY,
                    quote_id=quote_id,
                    conversation_id=conversation_id,
                )

            sent = await self.repo.latest_open_quote(conversation_id)
            if sent is not None and sent.status in ("sent", "followed_up"):
                # Any reply stops the follow-up timer (D-013).
                if self.followups is not None and self.followups.cancel(sent.id):
                    await self.repo.add_event(sent.id, "followup_cancelled", {"reason": "reply"})
                if ACCEPT.match(text):
                    return await self._accept(conversation_id, sent.id, sent.number)

            out = await self.graph.ainvoke(
                {"conversation_id": conversation_id, "customer": customer, "raw_query": text},
                _config(conversation_id),
            )
            return await self._finish(conversation_id, out)

    async def _accept(self, conversation_id: str, quote_id: str, number: str) -> TurnResult:
        await self.repo.set_status(quote_id, "accepted", event={"by": "customer"})
        reply = REPLY_ACCEPTED.format(number=number)
        await self.repo.add_message(conversation_id, "business", reply, quote_id=quote_id)
        return TurnResult(
            status="completed", reply=reply, quote_id=quote_id, conversation_id=conversation_id
        )

    async def decide(
        self, quote_id: str, decision: Approve | Reject | Edit, *, revision: int | None = None
    ) -> TurnResult:
        quote = await self.repo.get_quote(quote_id)
        if quote is None:
            raise NotFoundError(quote_id)
        conversation_id = quote.conversation_id
        async with self._locks[conversation_id]:
            waiting = await self.pending(conversation_id)
            if waiting is None or waiting["quote_id"] != quote_id:
                raise QuoteNotPendingError(quote_id)
            if revision is not None and revision != waiting["revision"]:
                raise StaleRevisionError(f"quote is at revision {waiting['revision']}")
            out = await self.graph.ainvoke(
                Command(resume=decision.model_dump(mode="json")), _config(conversation_id)
            )
            return await self._finish(conversation_id, out)

    async def _finish(self, conversation_id: str, out: dict[str, Any]) -> TurnResult:
        quote_id = out.get("quote_id")
        reply = out.get("reply") or ""
        if "__interrupt__" in out:
            status: TurnStatus = "awaiting_approval"
        elif out.get("outcome") == "needs_clarification":
            status = "needs_clarification"
        elif out.get("outcome") == "rejected":
            status = "rejected"
        else:
            status = "completed"
        if reply:
            await self.repo.add_message(
                conversation_id,
                "business",
                reply,
                quote_id=quote_id,
                kind=out.get("reply_kind") or "text",
            )
        return TurnResult(
            status=status, reply=reply, quote_id=quote_id, conversation_id=conversation_id
        )
