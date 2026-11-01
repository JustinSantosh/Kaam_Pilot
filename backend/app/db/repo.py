"""Repository for conversations, messages and quotes. Every write is idempotent where a graph
node might repeat it (D-007, D-010)."""

import secrets
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Conversation, Message, Quote, QuoteEvent, QuoteItem, utcnow
from app.schemas.pricing import PricedQuote

OPEN_STATUSES = ("draft", "awaiting_approval", "approved", "sent", "followed_up")
TERMINAL_STATUSES = ("accepted", "rejected", "cancelled", "lapsed")


class NotFoundError(LookupError):
    pass


def new_quote_id() -> str:
    return f"q_{secrets.token_hex(6)}"


class Repo:
    def __init__(self, sessions: async_sessionmaker) -> None:
        self.sessions = sessions

    # --- conversations & messages -----------------------------------------------------------------

    async def ensure_conversation(
        self, conversation_id: str, *, name: str = "", phone: str = "", state: str | None = None
    ) -> Conversation:
        async with self.sessions() as s, s.begin():
            conv = await s.get(Conversation, conversation_id)
            if conv is None:
                conv = Conversation(
                    id=conversation_id,
                    customer_name=name,
                    customer_phone=phone,
                    customer_state=state,
                )
                s.add(conv)
            else:
                conv.customer_name = name or conv.customer_name
                conv.customer_phone = phone or conv.customer_phone
                conv.customer_state = state or conv.customer_state
            return conv

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        async with self.sessions() as s:
            return await s.get(Conversation, conversation_id)

    async def conversations(self, ids: Iterable[str]) -> dict[str, Conversation]:
        ids = list(set(ids))
        if not ids:
            return {}
        async with self.sessions() as s:
            rows = await s.scalars(select(Conversation).where(Conversation.id.in_(ids)))
            return {c.id: c for c in rows}

    async def revisions(self, quote_id: str) -> list[int]:
        async with self.sessions() as s:
            rows = await s.scalars(
                select(QuoteItem.revision)
                .where(QuoteItem.quote_id == quote_id)
                .distinct()
                .order_by(QuoteItem.revision)
            )
            return list(rows)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        *,
        quote_id: str | None = None,
        kind: str = "text",
    ) -> Message:
        async with self.sessions() as s, s.begin():
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                text=text,
                quote_id=quote_id,
                kind=kind,
            )
            s.add(msg)
        return msg

    async def list_messages(self, conversation_id: str, since_id: int = 0) -> list[Message]:
        async with self.sessions() as s:
            rows = await s.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id, Message.id > since_id)
                .order_by(Message.id)
            )
            return list(rows)

    async def last_customer_message_at(self, conversation_id: str) -> datetime | None:
        async with self.sessions() as s:
            return await s.scalar(
                select(func.max(Message.created_at)).where(
                    Message.conversation_id == conversation_id, Message.role == "customer"
                )
            )

    # --- quotes -----------------------------------------------------------------------------------

    async def _next_number(self, s: Any) -> str:
        prefix = f"KP-{utcnow().year}-"
        count = await s.scalar(select(func.count()).where(Quote.number.like(f"{prefix}%")))
        return f"{prefix}{(count or 0) + 1:04d}"

    async def create_quote(
        self,
        conversation_id: str,
        *,
        raw_query: str,
        extraction: dict,
        validation: dict,
        customer_state: str | None,
    ) -> Quote:
        async with self.sessions() as s, s.begin():
            quote = Quote(
                id=new_quote_id(),
                number=await self._next_number(s),
                conversation_id=conversation_id,
                status="draft",
                revision=0,
                raw_query=raw_query,
                extraction=extraction,
                validation=validation,
                customer_state=customer_state,
            )
            s.add(quote)
            s.add(QuoteEvent(quote_id=quote.id, kind="created", payload={"number": quote.number}))
        return quote

    async def save_revision(
        self,
        quote_id: str,
        revision: int,
        priced: PricedQuote,
        *,
        discount: dict | None = None,
        flags: list[str] | None = None,
    ) -> Quote:
        """Write priced lines for `revision`. Re-running with the same revision replaces it."""
        async with self.sessions() as s, s.begin():
            quote = await s.get(Quote, quote_id)
            if quote is None:
                raise NotFoundError(quote_id)
            await s.execute(
                delete(QuoteItem).where(
                    QuoteItem.quote_id == quote_id, QuoteItem.revision == revision
                )
            )
            for pos, line in enumerate(priced.lines):
                s.add(
                    QuoteItem(
                        quote_id=quote_id, revision=revision, position=pos, **line.model_dump()
                    )
                )
            t = priced.totals
            quote.revision = revision
            quote.supply_type = priced.supply_type
            quote.flags = list(priced.flags if flags is None else flags)
            quote.discount = discount
            for field in (
                "subtotal_paise",
                "discount_paise",
                "taxable_paise",
                "cgst_paise",
                "sgst_paise",
                "igst_paise",
                "tax_paise",
                "total_paise",
            ):
                setattr(quote, field, getattr(t, field))
            s.add(
                QuoteEvent(
                    quote_id=quote_id,
                    kind="priced",
                    payload={"revision": revision, "total_paise": t.total_paise},
                )
            )
            return quote

    async def update_quote(self, quote_id: str, **fields: Any) -> Quote:
        async with self.sessions() as s, s.begin():
            quote = await s.get(Quote, quote_id)
            if quote is None:
                raise NotFoundError(quote_id)
            for key, value in fields.items():
                setattr(quote, key, value)
            return quote

    async def set_status(
        self, quote_id: str, status: str, *, event: dict | None = None, **fields: Any
    ) -> Quote:
        async with self.sessions() as s, s.begin():
            quote = await s.get(Quote, quote_id)
            if quote is None:
                raise NotFoundError(quote_id)
            previous = quote.status
            quote.status = status
            for key, value in fields.items():
                setattr(quote, key, value)
            s.add(
                QuoteEvent(
                    quote_id=quote_id,
                    kind=f"status:{status}",
                    payload={"from": previous, **(event or {})},
                )
            )
            return quote

    async def add_event(self, quote_id: str, kind: str, payload: dict | None = None) -> None:
        async with self.sessions() as s, s.begin():
            s.add(QuoteEvent(quote_id=quote_id, kind=kind, payload=payload or {}))

    async def get_quote(self, quote_id: str) -> Quote | None:
        async with self.sessions() as s:
            return await s.get(Quote, quote_id)

    async def get_items(self, quote_id: str, revision: int | None = None) -> list[QuoteItem]:
        async with self.sessions() as s:
            if revision is None:
                quote = await s.get(Quote, quote_id)
                if quote is None:
                    raise NotFoundError(quote_id)
                revision = quote.revision
            rows = await s.scalars(
                select(QuoteItem)
                .where(QuoteItem.quote_id == quote_id, QuoteItem.revision == revision)
                .order_by(QuoteItem.position)
            )
            return list(rows)

    async def get_events(self, quote_id: str) -> list[QuoteEvent]:
        async with self.sessions() as s:
            rows = await s.scalars(
                select(QuoteEvent).where(QuoteEvent.quote_id == quote_id).order_by(QuoteEvent.id)
            )
            return list(rows)

    async def list_quotes(self, statuses: Iterable[str] | None = None) -> list[Quote]:
        async with self.sessions() as s:
            query = select(Quote).order_by(Quote.created_at.desc())
            if statuses:
                query = query.where(Quote.status.in_(list(statuses)))
            return list(await s.scalars(query))

    async def item_counts(self, quote_ids: list[str]) -> dict[str, int]:
        if not quote_ids:
            return {}
        async with self.sessions() as s:
            rows = await s.execute(
                select(QuoteItem.quote_id, func.count())
                .join(
                    Quote, (Quote.id == QuoteItem.quote_id) & (Quote.revision == QuoteItem.revision)
                )
                .where(QuoteItem.quote_id.in_(quote_ids))
                .group_by(QuoteItem.quote_id)
            )
            return {qid: n for qid, n in rows.all()}

    async def latest_open_quote(self, conversation_id: str) -> Quote | None:
        async with self.sessions() as s:
            return await s.scalar(
                select(Quote)
                .where(Quote.conversation_id == conversation_id, Quote.status.in_(OPEN_STATUSES))
                .order_by(Quote.created_at.desc())
                .limit(1)
            )
