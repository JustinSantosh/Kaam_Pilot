"""Quotation PDF: Jinja2 HTML template rendered by xhtml2pdf (D-021).

The template only formats numbers that pricing already produced and the DB stored; it never
calculates anything, so the PDF always matches the quote (D-002).
"""

import io
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.config import Settings
from app.db.models import Conversation, Quote, QuoteItem
from app.services.money import paise_to_display
from app.services.states import STATES
from app.services.words import amount_in_words

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PDF_SYMBOL = "Rs. "

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))
_env.filters["money"] = lambda paise: paise_to_display(paise, PDF_SYMBOL)


class PdfError(RuntimeError):
    pass


@dataclass(frozen=True)
class TaxRow:
    label: str
    amount: int


def pdf_relpath(quote_id: str, revision: int, *, draft: bool) -> Path:
    """Path under the storage dir; also the shape of the public URL (Phase 07)."""
    return Path("quotes") / quote_id / f"r{revision}{'-draft' if draft else ''}.pdf"


def _tax_rows(quote: Quote, items: list[QuoteItem]) -> list[TaxRow]:
    rates = sorted({i.gst_rate_bp for i in items})
    rate_text = "/".join(f"{r / 100:g}%" for r in rates)
    if quote.supply_type == "inter_state":
        return [TaxRow(f"IGST @ {rate_text}", quote.igst_paise)]
    half = "/".join(f"{r / 200:g}%" for r in rates)
    return [TaxRow(f"CGST @ {half}", quote.cgst_paise), TaxRow(f"SGST @ {half}", quote.sgst_paise)]


def _flag_text(flag: str) -> str:
    if flag.startswith("customer_state_unknown"):
        return "Customer's state not known; GST shown as intra-state. Confirm before invoicing."
    return flag.replace("_", " ")


def render_html(
    quote: Quote,
    items: list[QuoteItem],
    conversation: Conversation | None,
    settings: Settings,
    *,
    draft: bool,
    issued: datetime | None = None,
) -> str:
    issued = issued or quote.created_at
    state = quote.customer_state
    place = f"{STATES[state]} ({state})" if state in STATES else "Not specified"
    return _env.get_template("quotation.html").render(
        business={
            "name": settings.business_name,
            "gstin": settings.business_gstin,
            "address": settings.business_address,
            "phone": settings.business_phone,
            "validity_days": settings.quote_validity_days,
            "advance_percent": settings.advance_percent,
        },
        quote=quote,
        items=items,
        customer={
            "name": conversation.customer_name if conversation else "",
            "phone": conversation.customer_phone if conversation else "",
        },
        place_of_supply=place,
        issued=issued.strftime("%d %b %Y"),
        valid_until=(issued + timedelta(days=settings.quote_validity_days)).strftime("%d %b %Y"),
        tax_rows=_tax_rows(quote, items),
        total_words=amount_in_words(quote.total_paise),
        flags=[_flag_text(f) for f in quote.flags or []],
        draft=draft,
    )


def render_pdf(
    quote: Quote,
    items: list[QuoteItem],
    conversation: Conversation | None,
    settings: Settings,
    *,
    draft: bool,
) -> Path:
    """Write the PDF under storage_dir and return its path relative to storage_dir."""
    html = render_html(quote, items, conversation, settings, draft=draft)
    buffer = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise PdfError(f"PDF rendering failed for {quote.id} r{quote.revision}")
    rel = pdf_relpath(quote.id, quote.revision, draft=draft)
    target = settings.storage_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(buffer.getvalue())
    return rel
