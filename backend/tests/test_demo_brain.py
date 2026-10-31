"""The offline demo brain (D-022): presets run end to end through the real graph."""

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.agent.deps import DEMO_MODEL
from app.config import Settings
from app.llm.demo import DemoBrain, scenarios
from app.main import create_app
from app.services.catalog import load_catalog
from app.services.validator import validate

CATALOG = load_catalog()


@pytest.fixture
async def demo_client(tmp_path: Path):  # noqa: ANN201
    settings = Settings(storage_dir=tmp_path / "s", llm_model=DEMO_MODEL, _env_file=None)
    app: FastAPI = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            yield client


@pytest.mark.parametrize("scenario", scenarios(), ids=lambda s: s["id"])
async def test_every_preset_has_a_sensible_intent(scenario: dict) -> None:
    intent = (await DemoBrain().classify_intent(scenario["message"])).intent
    expected = {"cancel": "cancel", "off-topic": "other"}.get(scenario["id"], "new_quote")
    assert intent == expected


async def test_complete_presets_validate() -> None:
    brain = DemoBrain()
    for sc in scenarios():
        if sc["id"] in ("complete-apparel", "fabrication-multi"):
            assert validate(await brain.extract(sc["message"]), CATALOG).complete, sc["id"]
    hinglish = next(s for s in scenarios() if s["id"] == "hinglish-incomplete")
    joined = f"{hinglish['message']}\n{hinglish['follow_up']['message']}"
    assert not validate(await brain.extract(hinglish["message"]), CATALOG).complete
    assert validate(await brain.extract(joined), CATALOG).complete


async def test_heuristic_free_text() -> None:
    brain = DemoBrain()
    result = await brain.extract("50 black hoodies, DTF on back, M 20 L 20 XL 10")
    item = result.items[0]
    assert item.item_text == "black hoodie"
    assert item.quantity == 50
    assert item.spec_dict() == {
        "print_type": "dtf",
        "placement": "back",
        "size_mix": "M:20, L:20, XL:10",
    }
    assert (await brain.extract("hello there")).items == []


async def test_demo_mode_runs_the_real_app(demo_client: httpx.AsyncClient) -> None:
    presets = (await demo_client.get("/api/demo/scenarios")).json()
    assert {p["id"] for p in presets} >= {"complete-apparel", "hinglish-incomplete"}
    complete = next(p for p in presets if p["id"] == "complete-apparel")
    resp = await demo_client.post(
        "/api/chat/send", json={"conversation_id": "d1", "message": complete["message"]}
    )
    assert resp.json()["status"] == "awaiting_approval"
    fab = next(p for p in presets if p["id"] == "fabrication-multi")
    resp = await demo_client.post(
        "/api/chat/send", json={"conversation_id": "d2", "message": fab["message"]}
    )
    detail = (await demo_client.get(f"/api/quotes/{resp.json()['quote_id']}")).json()
    assert [(i["sku"], i["quantity"]) for i in detail["items"]] == [
        ("GATE-MS", 72),
        ("RAIL-SS", 24),
    ]
    assert detail["supply_type"] == "inter_state"
