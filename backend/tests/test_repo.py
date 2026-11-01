import asyncio

from app.db.repo import Repo
from app.schemas.pricing import PricingInput
from app.services.catalog import load_catalog
from app.services.pricing import price_quote
from app.services.states import state_code

CATALOG = load_catalog()


def priced(qty: int):
    return price_quote(
        [
            PricingInput(
                sku="HOOD-BLK",
                quantity=qty,
                specs={"size_mix": "M:10", "print_type": "dtf", "placement": "back"},
            )
        ],
        catalog=CATALOG,
        business_state="CG",
        customer_state="CG",
    )


async def make_quote(repo: Repo, conv: str = "c1"):
    await repo.ensure_conversation(conv, name="Ravi")
    return await repo.create_quote(
        conv, raw_query="x", extraction={}, validation={}, customer_state="CG"
    )


async def test_quote_numbers_are_sequential(repo: Repo) -> None:
    first, second = await make_quote(repo), await make_quote(repo)
    assert first.number.endswith("-0001")
    assert second.number.endswith("-0002")


async def test_concurrent_quotes_get_distinct_numbers(repo: Repo) -> None:
    await repo.ensure_conversation("c1", name="Ravi")
    quotes = await asyncio.gather(
        *(
            repo.create_quote(
                "c1", raw_query="x", extraction={}, validation={}, customer_state="CG"
            )
            for _ in range(20)  # without the lock, several collide on the unique number
        )
    )
    assert len({q.number for q in quotes}) == 20


async def test_save_revision_is_idempotent_and_keeps_history(repo: Repo) -> None:
    quote = await make_quote(repo)
    await repo.save_revision(quote.id, 1, priced(10))
    await repo.save_revision(quote.id, 1, priced(10))  # replay
    await repo.save_revision(quote.id, 2, priced(20))

    assert len(await repo.get_items(quote.id, 1)) == 1
    assert (await repo.get_items(quote.id))[0].quantity == 20
    stored = await repo.get_quote(quote.id)
    assert stored.revision == 2
    assert stored.total_paise == priced(20).totals.total_paise


async def test_list_quotes_by_status_and_counts(repo: Repo) -> None:
    a, b = await make_quote(repo), await make_quote(repo)
    await repo.save_revision(a.id, 1, priced(10))
    await repo.set_status(b.id, "awaiting_approval")
    waiting = await repo.list_quotes(["awaiting_approval"])
    assert [q.id for q in waiting] == [b.id]
    assert await repo.item_counts([a.id, b.id]) == {a.id: 1}


async def test_status_changes_are_audited(repo: Repo) -> None:
    quote = await make_quote(repo)
    await repo.set_status(quote.id, "awaiting_approval")
    await repo.set_status(
        quote.id, "rejected", event={"reason": "no stock"}, rejection_reason="no stock"
    )
    kinds = [e.kind for e in await repo.get_events(quote.id)]
    assert kinds == ["created", "status:awaiting_approval", "status:rejected"]
    assert (await repo.get_quote(quote.id)).rejection_reason == "no stock"


async def test_messages_since_cursor(repo: Repo) -> None:
    await repo.ensure_conversation("c2")
    first = await repo.add_message("c2", "customer", "hi")
    await repo.add_message("c2", "business", "hello")
    assert [m.text for m in await repo.list_messages("c2")] == ["hi", "hello"]
    assert [m.text for m in await repo.list_messages("c2", since_id=first.id)] == ["hello"]


def test_state_codes() -> None:
    assert state_code("Maharashtra") == "MH"
    assert state_code("mh") == "MH"
    assert state_code("  Raipur ") == "CG"
    assert state_code("Chattisgarh") == "CG"
    assert state_code("Atlantis") is None
    assert state_code("Bilaspur") is None  # a city in both CG and HP: flag, don't guess
    assert state_code(None) is None
