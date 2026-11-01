"""End-to-end over HTTP with the LLM faked (Phase 07 exit criteria)."""

import httpx

from app.agent.runtime import REPLY_BUSY
from tests.fakes import FakeBrain, tee

CUSTOMER = {"name": "Ravi", "phone": "+91 99999 11111", "state": "CG"}


async def send(client: httpx.AsyncClient, text: str, conv: str = "c_api") -> dict:
    resp = await client.post(
        "/api/chat/send", json={"conversation_id": conv, "customer": CUSTOMER, "message": text}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_full_flow(client: httpx.AsyncClient, brain: FakeBrain) -> None:
    brain.when("60 black tees front screen", tee(60, sizes=False))
    brain.when("60 black tees front screen\nsizes M 60", tee(60))

    # 1. incomplete → clarification question
    first = await send(client, "60 black tees front screen")
    assert first["status"] == "needs_clarification"
    assert "sizes" in first["reply"]

    # 2. follow-up completes it → awaiting approval
    second = await send(client, "sizes M 60")
    assert second["status"] == "awaiting_approval"
    quote_id = second["quote_id"]

    # 3. inbox lists it; detail has extraction, items, totals and a downloadable PDF
    inbox = (await client.get("/api/business/inbox")).json()
    assert [q["quote_id"] for q in inbox] == [quote_id]
    assert inbox[0]["customer_name"] == "Ravi"
    assert inbox[0]["item_count"] == 1

    detail = (await client.get(f"/api/quotes/{quote_id}")).json()
    assert detail["status"] == "awaiting_approval"
    assert detail["items"][0]["sku"] == "TEE-RN-BLK"
    assert detail["extraction"]["items"][0]["quantity"] == 60
    assert detail["totals"]["total_paise"] == detail["total_paise"]
    pdf = await client.get(detail["pdf_url"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # 4. edit → revision 2, then approve
    edited = await client.post(
        f"/api/quotes/{quote_id}/decision?revision=1",
        json={"action": "edit", "edits": {"items": [{"sku": "TEE-RN-BLK", "quantity": 80}]}},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["revision"] == 2
    assert edited.json()["revisions"] == [1, 2]
    assert edited.json()["items"][0]["quantity"] == 80

    approved = await client.post(
        f"/api/quotes/{quote_id}/decision?revision=2", json={"action": "approve"}
    )
    assert approved.json()["status"] == "approved"
    assert approved.json()["pdf_url"].endswith("/r2.pdf")

    # 5. second approve → 409
    again = await client.post(f"/api/quotes/{quote_id}/decision", json={"action": "approve"})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "quote_not_pending"

    # chat history, oldest first; polling with `since` returns only newer messages
    msgs = (await client.get("/api/conversations/c_api/messages")).json()
    assert [m["role"] for m in msgs][:2] == ["customer", "business"]
    newer = (await client.get(f"/api/conversations/c_api/messages?since={msgs[-2]['id']}")).json()
    assert newer == msgs[-1:]


async def test_message_while_pending_is_busy(client: httpx.AsyncClient) -> None:
    hoodies = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
    started = await send(client, hoodies, conv="c_busy")
    busy = await send(client, "make it 70", conv="c_busy")
    assert busy["status"] == "busy"
    assert busy["reply"] == REPLY_BUSY
    detail = (await client.get(f"/api/quotes/{started['quote_id']}")).json()
    assert detail["customer_notes"] == ["make it 70"]


async def test_stale_revision_and_invalid_edit(client: httpx.AsyncClient) -> None:
    hoodies = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
    quote_id = (await send(client, hoodies, conv="c_edit"))["quote_id"]

    stale = await client.post(
        f"/api/quotes/{quote_id}/decision?revision=5", json={"action": "approve"}
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_revision"

    bad = await client.post(
        f"/api/quotes/{quote_id}/decision",
        json={"action": "edit", "edits": {"items": [{"sku": "HOOD-BLK", "quantity": 2}]}},
    )
    assert bad.status_code == 200
    assert bad.json()["revision"] == 1
    assert "below MOQ" in bad.json()["edit_errors"][0]


async def test_reject_requires_reason(client: httpx.AsyncClient) -> None:
    hoodies = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
    quote_id = (await send(client, hoodies, conv="c_rej"))["quote_id"]
    missing = await client.post(f"/api/quotes/{quote_id}/decision", json={"action": "reject"})
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "validation_error"
    ok = await client.post(
        f"/api/quotes/{quote_id}/decision", json={"action": "reject", "reason": "No stock"}
    )
    assert ok.json()["status"] == "rejected"
    closed = (await client.get("/api/business/inbox?status=closed")).json()
    assert [q["quote_id"] for q in closed] == [quote_id]


async def test_validation_and_not_found(client: httpx.AsyncClient) -> None:
    bad_id = await client.post(
        "/api/chat/send", json={"conversation_id": "../etc", "message": "hi"}
    )
    assert bad_id.status_code == 422
    empty = await client.post("/api/chat/send", json={"conversation_id": "c1", "message": ""})
    assert empty.status_code == 422
    missing = await client.get("/api/quotes/q_000000000000")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    assert (await client.get("/api/business/inbox?status=weird")).status_code == 422


async def test_catalog_for_edit_drawer(client: httpx.AsyncClient) -> None:
    items = (await client.get("/api/business/catalog")).json()
    tee_item = next(i for i in items if i["sku"] == "TEE-RN-BLK")
    assert tee_item["moq"] == 20
    assert tee_item["spec_options"]["print_type"] == ["dtf", "embroidery", "screen"]


async def test_openapi_lists_routes(client: httpx.AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    for path in (
        "/api/chat/send",
        "/api/conversations/{conversation_id}/messages",
        "/api/business/inbox",
        "/api/business/catalog",
        "/api/quotes/{quote_id}",
        "/api/quotes/{quote_id}/decision",
    ):
        assert path in paths
