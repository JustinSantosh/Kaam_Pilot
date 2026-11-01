"""Human-in-the-loop: pause, survive a restart, resume with approve / edit / reject (Phase 05)."""

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import build_graph
from app.agent.nodes import REPLY_APPROVED, REPLY_PREPARING, REPLY_REJECTED
from app.agent.runtime import (
    REPLY_BUSY,
    QuoteNotPendingError,
    Runtime,
    StaleRevisionError,
    TurnResult,
)
from app.config import Settings
from app.db.repo import Repo
from app.db.session import CHECKPOINTS_DB
from app.schemas.decision import Approve, DecisionAdapter, Edit, Reject
from app.services.catalog import load_catalog
from app.services.money import paise_to_display
from tests.fakes import FakeBrain

HOODIES = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
CUSTOMER = {"name": "Ravi", "phone": "+910000000000", "state": "CG"}


@pytest.fixture
def runtime(app) -> Runtime:  # noqa: ANN001
    return app.state.runtime


async def start(runtime: Runtime, conv: str = "c1") -> TurnResult:
    result = await runtime.handle_message(conv, HOODIES, customer=CUSTOMER)
    assert result.status == "awaiting_approval"
    return result


def edit(**edits) -> Edit:  # noqa: ANN003
    return DecisionAdapter.validate_python({"action": "edit", "edits": edits})


async def kinds(repo: Repo, quote_id: str) -> list[str]:
    return [e.kind for e in await repo.get_events(quote_id)]


async def test_pause_exposes_review_payload(runtime: Runtime, repo: Repo) -> None:
    result = await start(runtime)
    quote = await repo.get_quote(result.quote_id)
    assert quote.status == "awaiting_approval"
    assert result.reply == REPLY_PREPARING.format(number=quote.number)

    payload = await runtime.pending("c1")
    assert payload["quote_id"] == result.quote_id
    assert payload["revision"] == 1
    assert payload["totals"]["total_paise"] == quote.total_paise


async def test_approve_after_restart_runs_dispatch_once(
    runtime: Runtime, repo: Repo, settings: Settings, brain: FakeBrain
) -> None:
    result = await start(runtime)
    # A brand-new graph + checkpointer on the same files, as after a server restart.
    deps = brain.deps_factory(load_catalog(), repo, settings)
    async with AsyncSqliteSaver.from_conn_string(
        str(settings.storage_dir / CHECKPOINTS_DB)
    ) as saver:
        fresh = Runtime(build_graph(deps, saver), repo)
        done = await fresh.decide(result.quote_id, Approve(action="approve"))
        assert await fresh.pending("c1") is None

    quote = await repo.get_quote(result.quote_id)
    assert done.status == "completed"
    assert quote.status == "sent"
    assert done.reply == REPLY_APPROVED.format(
        number=quote.number, total=paise_to_display(quote.total_paise)
    )
    assert (await kinds(repo, result.quote_id)).count("status:sent") == 1


async def test_edit_reprices_into_new_revision(runtime: Runtime, repo: Repo) -> None:
    result = await start(runtime)
    before = await repo.get_quote(result.quote_id)

    edited = await runtime.decide(
        result.quote_id, edit(items=[{"sku": "HOOD-BLK", "quantity": 60}]), revision=1
    )
    assert edited.status == "awaiting_approval"
    assert edited.reply == ""  # the customer isn't told about internal edits
    after = await repo.get_quote(result.quote_id)
    assert after.revision == 2
    assert (await repo.get_items(result.quote_id))[0].quantity == 60
    assert (await repo.get_items(result.quote_id, 1))[0].quantity == 50  # history kept
    assert after.total_paise > before.total_paise
    assert (await repo.get_items(result.quote_id))[0].specs["print_type"] == "dtf"  # kept

    await runtime.decide(result.quote_id, Approve(action="approve"), revision=2)
    assert (await repo.get_quote(result.quote_id)).status == "sent"


async def test_discount_is_taxed_after_discount(runtime: Runtime, repo: Repo) -> None:
    result = await start(runtime)
    await runtime.decide(result.quote_id, edit(discount={"kind": "percent", "value": 1000}))
    quote = await repo.get_quote(result.quote_id)
    assert quote.discount_paise == round(quote.subtotal_paise / 10)
    assert quote.taxable_paise == quote.subtotal_paise - quote.discount_paise
    assert quote.tax_paise == quote.cgst_paise + quote.sgst_paise
    assert quote.cgst_paise == round(quote.taxable_paise * 0.025)

    await runtime.decide(result.quote_id, edit(remove_discount=True))
    assert (await repo.get_quote(result.quote_id)).discount_paise == 0


async def test_invalid_edit_returns_errors_without_new_revision(
    runtime: Runtime, repo: Repo
) -> None:
    result = await start(runtime)
    again = await runtime.decide(result.quote_id, edit(items=[{"sku": "HOOD-BLK", "quantity": 3}]))
    assert again.status == "awaiting_approval"
    payload = await runtime.pending("c1")
    assert payload["revision"] == 1
    assert "below MOQ" in payload["edit_errors"][0]
    assert "edit_rejected" in await kinds(repo, result.quote_id)
    assert (await repo.get_quote(result.quote_id)).revision == 1


async def test_reject_records_reason(runtime: Runtime, repo: Repo) -> None:
    result = await start(runtime)
    done = await runtime.decide(result.quote_id, Reject(action="reject", reason="No stock"))
    quote = await repo.get_quote(result.quote_id)
    assert done.status == "rejected"
    assert quote.status == "rejected"
    assert quote.rejection_reason == "No stock"
    assert done.reply == REPLY_REJECTED.format(number=quote.number)


async def test_no_duplicate_events_from_resume_replay(runtime: Runtime, repo: Repo) -> None:
    result = await start(runtime)
    await runtime.decide(result.quote_id, edit(items=[{"sku": "HOOD-BLK", "quantity": 55}]))
    await runtime.decide(result.quote_id, Approve(action="approve"))
    assert await kinds(repo, result.quote_id) == [
        "created",
        "priced",
        "status:awaiting_approval",
        "edited",
        "priced",
        "status:awaiting_approval",
        "status:approved",
        "status:sent",
        "followup_scheduled",
    ]


async def test_customer_message_while_pending_is_a_note(
    runtime: Runtime, repo: Repo, brain: FakeBrain
) -> None:
    result = await start(runtime)
    calls = len(brain.intent_calls)
    busy = await runtime.handle_message("c1", "make it 70 please", customer=CUSTOMER)

    assert busy.status == "busy"
    assert busy.reply == REPLY_BUSY
    assert len(brain.intent_calls) == calls  # graph not started
    assert (await runtime.pending("c1"))["quote_id"] == result.quote_id
    assert "customer_note" in await kinds(repo, result.quote_id)
    texts = [(m.role, m.text) for m in await repo.list_messages("c1")]
    assert texts[-2:] == [("customer", "make it 70 please"), ("business", REPLY_BUSY)]


async def test_decisions_on_wrong_quote_or_revision_fail(runtime: Runtime) -> None:
    result = await start(runtime)
    with pytest.raises(StaleRevisionError):
        await runtime.decide(result.quote_id, Approve(action="approve"), revision=7)
    await runtime.decide(result.quote_id, Approve(action="approve"))
    with pytest.raises(QuoteNotPendingError):
        await runtime.decide(result.quote_id, Approve(action="approve"))


async def test_new_request_after_approval_creates_new_quote(runtime: Runtime) -> None:
    first = await start(runtime)
    await runtime.decide(first.quote_id, Approve(action="approve"))
    second = await start(runtime)
    assert second.quote_id != first.quote_id
