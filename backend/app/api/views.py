"""Turn records-DB rows into API models (D-007: the API reads the records DB, never checkpoints,
except `pending` edit errors which only exist in the paused run)."""

from app.db.models import Conversation, Message, Quote, QuoteItem
from app.db.repo import Repo
from app.schemas.api import EventOut, MessageOut, QuoteDetail, QuoteSummary
from app.schemas.pricing import PricedLineItem, QuoteTotals

TOTAL_FIELDS = (
    "subtotal_paise", "discount_paise", "taxable_paise", "cgst_paise", "sgst_paise",
    "igst_paise", "tax_paise", "total_paise",
)  # fmt: skip


def pdf_url(pdf_path: str | None) -> str | None:
    return f"/files/{pdf_path}" if pdf_path else None


def message_out(m: Message, quote_pdf: dict[str, str | None] | None = None) -> MessageOut:
    url = (quote_pdf or {}).get(m.quote_id) if m.kind == "quote" and m.quote_id else None
    return MessageOut(
        id=m.id, role=m.role, text=m.text, kind=m.kind, quote_id=m.quote_id,
        pdf_url=pdf_url(url), created_at=m.created_at,
    )  # fmt: skip


def summary(q: Quote, conv: Conversation | None, item_count: int) -> QuoteSummary:
    return QuoteSummary(
        quote_id=q.id,
        number=q.number,
        conversation_id=q.conversation_id,
        customer_name=conv.customer_name if conv else "",
        status=q.status,
        revision=q.revision,
        total_paise=q.total_paise,
        item_count=item_count,
        flags=list(q.flags or []),
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


def _line(i: QuoteItem) -> PricedLineItem:
    return PricedLineItem.model_validate(i, from_attributes=True)


async def detail(repo: Repo, q: Quote, edit_errors: list[str]) -> QuoteDetail:
    conv = await repo.get_conversation(q.conversation_id)
    items = await repo.get_items(q.id)
    events = await repo.get_events(q.id)
    base = summary(q, conv, len(items)).model_dump()
    return QuoteDetail(
        **base,
        customer_phone=conv.customer_phone if conv else "",
        customer_state=q.customer_state,
        supply_type=q.supply_type,
        raw_query=q.raw_query,
        extraction=q.extraction or {},
        validation=q.validation or {},
        items=[_line(i) for i in items],
        totals=QuoteTotals(**{f: getattr(q, f) for f in TOTAL_FIELDS}),
        discount=q.discount,
        pdf_url=pdf_url(q.pdf_path),
        rejection_reason=q.rejection_reason,
        customer_notes=[e.payload.get("text", "") for e in events if e.kind == "customer_note"],
        edit_errors=edit_errors,
        revisions=await repo.revisions(q.id),
        events=[EventOut(kind=e.kind, payload=e.payload, created_at=e.created_at) for e in events],
    )
