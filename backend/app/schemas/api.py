"""HTTP request/response models (docs/project.md §6). Money is integer paise; the frontend only
formats it (D-005)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.pricing import PricedLineItem, QuoteTotals

ConversationId = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class CustomerIn(BaseModel):
    name: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    state: str | None = Field(default=None, max_length=60)


class ChatSendRequest(BaseModel):
    conversation_id: str = ConversationId
    customer: CustomerIn = Field(default_factory=CustomerIn)
    message: str = Field(min_length=1, max_length=4000)


class ChatSendResponse(BaseModel):
    status: Literal["awaiting_approval", "needs_clarification", "completed", "rejected", "busy"]
    reply: str
    quote_id: str | None
    conversation_id: str


class MessageOut(BaseModel):
    id: int
    role: str
    text: str
    kind: str
    quote_id: str | None
    pdf_url: str | None = None
    created_at: datetime


class QuoteSummary(BaseModel):
    quote_id: str
    number: str
    conversation_id: str
    customer_name: str
    status: str
    revision: int
    total_paise: int
    item_count: int
    flags: list[str]
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    kind: str
    payload: dict[str, Any]
    created_at: datetime


class QuoteDetail(QuoteSummary):
    customer_phone: str
    customer_state: str | None
    supply_type: str | None
    raw_query: str
    extraction: dict[str, Any]
    validation: dict[str, Any]
    items: list[PricedLineItem]
    totals: QuoteTotals
    discount: dict[str, Any] | None
    pdf_url: str | None
    rejection_reason: str | None
    customer_notes: list[str]
    edit_errors: list[str]
    revisions: list[int]
    events: list[EventOut]


class CatalogOption(BaseModel):
    sku: str
    name: str
    category: str
    unit: str
    moq: int
    required_specs: list[str]
    spec_options: dict[str, list[str]]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorBody
