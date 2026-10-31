"""Records DB: the system of record for conversations and quotes (D-007).

LangGraph checkpoints only hold paused workflow state; everything the inbox, audit trail and
customer chat need lives here. Money columns are integer paise (D-005).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(200), default="")
    customer_phone: Mapped[str] = mapped_column(String(40), default="")
    customer_state: Mapped[str | None] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # customer | business
    text: Mapped[str] = mapped_column(Text)
    quote_id: Mapped[str | None] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(32), default="text")  # text | quote | voice
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    revision: Mapped[int] = mapped_column(default=0)
    raw_query: Mapped[str] = mapped_column(Text, default="")
    extraction: Mapped[dict[str, Any]] = mapped_column(default=dict)
    validation: Mapped[dict[str, Any]] = mapped_column(default=dict)
    supply_type: Mapped[str | None] = mapped_column(String(16))
    customer_state: Mapped[str | None] = mapped_column(String(4))
    flags: Mapped[list[Any]] = mapped_column(default=list)
    subtotal_paise: Mapped[int] = mapped_column(default=0)
    discount_paise: Mapped[int] = mapped_column(default=0)
    taxable_paise: Mapped[int] = mapped_column(default=0)
    cgst_paise: Mapped[int] = mapped_column(default=0)
    sgst_paise: Mapped[int] = mapped_column(default=0)
    igst_paise: Mapped[int] = mapped_column(default=0)
    tax_paise: Mapped[int] = mapped_column(default=0)
    total_paise: Mapped[int] = mapped_column(default=0)
    discount: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # owner discount input
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column()


class QuoteItem(Base):
    __tablename__ = "quote_items"
    __table_args__ = (UniqueConstraint("quote_id", "revision", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), index=True)
    revision: Mapped[int]
    position: Mapped[int]
    sku: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    hsn: Mapped[str] = mapped_column(String(8))
    unit: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int]
    specs: Mapped[dict[str, Any]] = mapped_column(default=dict)
    unit_price_paise: Mapped[int]
    setup_fee_paise: Mapped[int]
    line_subtotal_paise: Mapped[int]
    discount_paise: Mapped[int]
    taxable_paise: Mapped[int]
    gst_rate_bp: Mapped[int]
    cgst_paise: Mapped[int]
    sgst_paise: Mapped[int]
    igst_paise: Mapped[int]
    line_total_paise: Mapped[int]


class QuoteEvent(Base):
    __tablename__ = "quote_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
