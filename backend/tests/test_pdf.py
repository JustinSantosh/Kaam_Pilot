"""Quotation PDFs (Phase 06): numbers in the PDF are exactly the stored quote's numbers."""

import io
from pathlib import Path

import httpx
import pytest
from pypdf import PdfReader

from app.agent.runtime import Runtime, TurnResult
from app.config import Settings
from app.db.repo import Repo
from app.schemas.decision import Approve, DecisionAdapter
from app.services.money import paise_to_display
from app.services.words import amount_in_words, number_in_words

HOODIES = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
POLOS = (
    "Quote for 30 navy polos with embroidered logo on chest, sizes: M-10, L-10, XL-10. "
    "Office in Mumbai."
)


@pytest.mark.parametrize(
    ("n", "words"),
    [
        (0, "Zero"),
        (15, "Fifteen"),
        (42, "Forty-Two"),
        (100, "One Hundred"),
        (1005, "One Thousand Five"),
        (100000, "One Lakh"),
        (1239000, "Twelve Lakh Thirty-Nine Thousand"),
        (25000000, "Two Crore Fifty Lakh"),
        (123456789, "Twelve Crore Thirty-Four Lakh Fifty-Six Thousand Seven Hundred Eighty-Nine"),
    ],
)
def test_number_in_words(n: int, words: str) -> None:
    assert number_in_words(n) == words


def test_amount_in_words() -> None:
    assert amount_in_words(123900050) == (
        "Twelve Lakh Thirty-Nine Thousand Rupees and Fifty Paise Only"
    )
    assert amount_in_words(100) == "One Rupee Only"
    assert amount_in_words(201) == "Two Rupees and One Paisa Only"


def pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(path.read_bytes())).pages)


def money(paise: int) -> str:
    return paise_to_display(paise, "Rs. ")


@pytest.fixture
def runtime(app) -> Runtime:  # noqa: ANN001
    return app.state.runtime


async def start(runtime: Runtime, text: str = HOODIES, state: str | None = "CG") -> TurnResult:
    result = await runtime.handle_message("c1", text, customer={"name": "Ravi", "state": state})
    assert result.status == "awaiting_approval"
    return result


async def test_draft_pdf_matches_stored_totals(
    runtime: Runtime, repo: Repo, settings: Settings
) -> None:
    result = await start(runtime)
    quote = await repo.get_quote(result.quote_id)
    assert quote.pdf_path == f"quotes/{quote.id}/r1-draft.pdf"

    text = pdf_text(settings.storage_dir / quote.pdf_path)
    assert quote.number in text
    assert "DRAFT" in text
    assert "Ravi" in text
    assert "Chhattisgarh (CG)" in text
    assert money(quote.subtotal_paise) in text
    assert money(quote.total_paise) in text
    assert "CGST @ 2.5%" in text and "SGST @ 2.5%" in text
    assert money(quote.cgst_paise) in text
    assert amount_in_words(quote.total_paise).split(" Rupees")[0].split()[0] in text


async def test_inter_state_pdf_shows_igst(runtime: Runtime, repo: Repo, settings: Settings) -> None:
    result = await runtime.handle_message("c2", POLOS, customer={"name": "Asha"})
    quote = await repo.get_quote(result.quote_id)
    text = pdf_text(settings.storage_dir / quote.pdf_path)
    assert "IGST @ 5%" in text
    assert "CGST" not in text
    assert "Maharashtra (MH)" in text


async def test_edit_makes_new_draft_and_keeps_old(
    runtime: Runtime, repo: Repo, settings: Settings
) -> None:
    result = await start(runtime)
    first = settings.storage_dir / f"quotes/{result.quote_id}/r1-draft.pdf"
    before = first.read_bytes()
    edit = DecisionAdapter.validate_python(
        {"action": "edit", "edits": {"items": [{"sku": "HOOD-BLK", "quantity": 60}]}}
    )
    await runtime.decide(result.quote_id, edit)

    quote = await repo.get_quote(result.quote_id)
    assert quote.pdf_path == f"quotes/{quote.id}/r2-draft.pdf"
    assert first.read_bytes() == before
    assert money(quote.total_paise) in pdf_text(settings.storage_dir / quote.pdf_path)


async def test_approval_renders_final_pdf_without_draft_mark(
    runtime: Runtime, repo: Repo, settings: Settings
) -> None:
    result = await start(runtime)
    await runtime.decide(result.quote_id, Approve(action="approve"))
    quote = await repo.get_quote(result.quote_id)
    assert quote.pdf_path == f"quotes/{quote.id}/r1.pdf"
    assert "DRAFT" not in pdf_text(settings.storage_dir / quote.pdf_path)


async def test_pdf_route_serves_and_rejects_bad_paths(
    runtime: Runtime, repo: Repo, client: httpx.AsyncClient
) -> None:
    result = await start(runtime)
    quote = await repo.get_quote(result.quote_id)
    ok = await client.get(f"/files/{quote.pdf_path}")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "application/pdf"
    assert ok.content.startswith(b"%PDF")

    for bad in (
        f"/files/quotes/{quote.id}/..%2F..%2Fkaampilot.db",
        f"/files/quotes/{quote.id}/r9.pdf",
        "/files/quotes/q_nothexnothex/r1.pdf",
        f"/files/quotes/{quote.id}/r1.txt",
    ):
        assert (await client.get(bad)).status_code == 404, bad
