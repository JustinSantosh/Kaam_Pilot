"""Graph paths with the LLM faked and real SQLite underneath (Phase 04)."""

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from app.agent.graph import build_graph
from app.agent.nodes import REPLY_NOTHING_TO_CANCEL, REPLY_OTHER
from app.config import Settings
from app.db.repo import Repo
from app.services.catalog import load_catalog
from tests.fakes import FakeBrain, tee

CONV = "c_test"
CUSTOMER = {"name": "Ravi", "phone": "+910000000000", "state": "CG"}


def cfg(thread: str = CONV) -> dict:
    return {"configurable": {"thread_id": thread}}


async def send(graph: CompiledStateGraph, text: str, thread: str = CONV) -> dict:
    return await graph.ainvoke(
        {"conversation_id": thread, "customer": CUSTOMER, "raw_query": text}, cfg(thread)
    )


async def test_other_message_gets_canned_reply(graph: CompiledStateGraph) -> None:
    out = await send(graph, "hello ji")
    assert out["outcome"] == "replied"
    assert out["reply"] == REPLY_OTHER


async def test_cancel_with_nothing_open(graph: CompiledStateGraph) -> None:
    out = await send(graph, "please cancel my order")
    assert out["outcome"] == "cancelled"
    assert out["reply"] == REPLY_NOTHING_TO_CANCEL


async def test_incomplete_request_asks_for_exact_missing_fields(
    graph: CompiledStateGraph, brain: FakeBrain
) -> None:
    brain.when("40 black tees front screen", tee(40, sizes=False))
    out = await send(graph, "40 black tees front screen")
    assert out["outcome"] == "needs_clarification"
    assert "sizes and how many of each" in out["reply"]
    assert out.get("quote_id") is None


async def test_clarification_continues_across_turns(
    graph: CompiledStateGraph, brain: FakeBrain, repo: Repo
) -> None:
    brain.when("50 black tees front screen", tee(50, sizes=False))
    brain.when("50 black tees front screen\nsizes M 50", tee(50))
    await send(graph, "50 black tees front screen")
    out = await send(graph, "sizes M 50")

    assert brain.extract_calls[-1] == "50 black tees front screen\nsizes M 50"
    assert out["quote_id"]
    assert out["revision"] == 1
    assert out["pending_inquiry"] == []
    quote = await repo.get_quote(out["quote_id"])
    assert quote is not None and quote.status == "awaiting_approval"


async def test_complete_request_creates_priced_quote(graph: CompiledStateGraph, repo: Repo) -> None:
    golden_input = (
        "Need 100 black round neck t-shirts, sizes S:20 M:40 L:40, screen print on front. "
        "Delivery by 20th Nov. We are in Raipur."
    )
    out = await send(graph, golden_input)
    quote = await repo.get_quote(out["quote_id"])
    items = await repo.get_items(out["quote_id"])

    # 100 × ₹200 tier + ₹500 setup = ₹20,500; intra-state 5% → ₹21,525
    assert quote.subtotal_paise == 2_050_000
    assert quote.total_paise == 2_152_500
    assert quote.supply_type == "intra_state"
    assert quote.number.startswith("KP-")
    assert [(i.sku, i.quantity) for i in items] == [("TEE-RN-BLK", 100)]
    assert out["totals"]["total_paise"] == quote.total_paise


async def test_customer_state_from_message_when_profile_has_none(
    graph: CompiledStateGraph, repo: Repo
) -> None:
    polo = (
        "Quote for 30 navy polos with embroidered logo on chest, sizes: M-10, L-10, XL-10. "
        "Office in Mumbai."
    )
    out = await graph.ainvoke(
        {"conversation_id": "c_mum", "customer": {"name": "Asha"}, "raw_query": polo},
        cfg("c_mum"),
    )
    quote = await repo.get_quote(out["quote_id"])
    assert quote.customer_state == "MH"
    assert quote.supply_type == "inter_state"
    assert quote.igst_paise > 0 and quote.cgst_paise == 0


async def test_cancel_cancels_latest_open_quote(graph: CompiledStateGraph, repo: Repo) -> None:
    created = await send(
        graph, "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
    )
    out = await send(graph, "cancel it please")
    assert out["outcome"] == "cancelled"
    assert (await repo.get_quote(created["quote_id"])).status == "cancelled"


async def test_state_survives_new_checkpointer_instance(
    settings: Settings, repo: Repo, brain: FakeBrain
) -> None:
    path = str(settings.storage_dir / "restart.db")
    brain.when("40 black tees front screen", tee(40, sizes=False))
    deps = brain.deps_factory(load_catalog(), repo, settings)

    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        await send(build_graph(deps, saver), "40 black tees front screen", "c_restart")

    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        snapshot = await build_graph(deps, saver).aget_state(cfg("c_restart"))
    assert snapshot.values["outcome"] == "needs_clarification"
    assert snapshot.values["pending_inquiry"] == ["40 black tees front screen"]
