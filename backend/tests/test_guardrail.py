"""Guardrails and voice (Phase 10). Correctness never depends on the guardrail: anything it lets
through is still priced only from the catalog (D-015)."""

import json
from pathlib import Path

import httpx
import pytest

from app.agent.nodes import REPLY_REFUSED
from app.agent.runtime import Runtime
from app.db.repo import Repo
from app.schemas.extraction import Extraction
from app.schemas.pricing import PricingInput
from app.services.catalog import load_catalog
from app.services.guardrail import FLAG_MONEY_OVERRIDE, check, rule_check
from app.services.pricing import price_quote
from tests.fakes import RiskyBrain
from tests.golden import load_golden

CASES = json.loads((Path(__file__).parent / "adversarial" / "cases.json").read_text("utf-8"))
HOODIE_SPECS = {"size_mix": "M:20, L:20, XL:10", "print_type": "dtf", "placement": "back"}
GOLDEN_HOODIES = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"


@pytest.fixture
def brain() -> RiskyBrain:
    brain = RiskyBrain()
    hoodies = brain.extractions[GOLDEN_HOODIES]
    for case in CASES:
        if case["expect"] == "quoted_flagged":
            brain.when(case["text"], hoodies)
        elif case["expect"] == "benign":
            brain.when(case["text"], Extraction())  # → clarifying question, not a refusal
    return brain


@pytest.fixture
def runtime(app) -> Runtime:  # noqa: ANN001
    return app.state.runtime


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
async def test_adversarial_cases(case: dict, runtime: Runtime, repo: Repo, brain) -> None:  # noqa: ANN001
    conv = f"adv_{case['id']}"
    result = await runtime.handle_message(conv, case["text"], customer={"state": "CG"})

    if case["expect"] in ("refused", "refused_llm"):
        assert result.reply == REPLY_REFUSED
        assert result.quote_id is None
        assert brain.extract_calls == []  # never reached extraction
        if case["expect"] == "refused":
            assert brain.risk_calls == []  # rules caught it; no LLM call spent
    elif case["expect"] == "quoted_flagged":
        assert result.status == "awaiting_approval"
        quote = await repo.get_quote(result.quote_id)
        assert FLAG_MONEY_OVERRIDE in quote.flags
        expected = price_quote(
            [PricingInput(sku="HOOD-BLK", quantity=50, specs=HOODIE_SPECS)],
            catalog=load_catalog(),
            business_state="CG",
            customer_state="CG",
        )
        assert quote.total_paise == expected.totals.total_paise  # money only from the catalog
    else:
        assert result.reply != REPLY_REFUSED
        assert not rule_check(case["text"]).flags


@pytest.mark.parametrize("case", load_golden(), ids=lambda c: c["id"])
def test_no_false_positives_on_golden_inquiries(case: dict) -> None:
    verdict = rule_check(case["input"])
    assert not verdict.flagged
    assert verdict.flags == []


async def test_risk_check_fails_open() -> None:
    brain = RiskyBrain()
    brain.fail_risk = True
    verdict = await check("50 black hoodies please", brain.classify_risk)
    assert not verdict.flagged
    assert verdict.source == "fail_open"


async def test_off_topic_from_llm_is_not_refused() -> None:
    async def off_topic(text: str):  # noqa: ANN202
        from app.schemas.extraction import RiskResult

        return RiskResult(risk="off_topic", reason="weather")

    verdict = await check("how is the weather", off_topic)
    assert not verdict.flagged
    assert verdict.risk == "off_topic"


# --- voice ----------------------------------------------------------------------------------------


async def test_voice_note_goes_through_the_same_pipeline(
    client: httpx.AsyncClient, brain: RiskyBrain, repo: Repo, settings
) -> None:  # noqa: ANN001
    audio = b"fake-webm-bytes"
    brain.transcripts[audio] = GOLDEN_HOODIES
    resp = await client.post(
        "/api/chat/send-audio",
        data={"conversation_id": "voice1", "name": "Ravi", "state": "CG"},
        files={"audio": ("note.webm", audio, "audio/webm;codecs=opus")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "awaiting_approval"
    messages = await repo.list_messages("voice1")
    assert (messages[0].role, messages[0].kind, messages[0].text) == (
        "customer",
        "voice",
        GOLDEN_HOODIES,
    )
    assert list((settings.storage_dir / "audio" / "voice1").glob("*.webm"))


async def test_voice_rejects_bad_uploads(client: httpx.AsyncClient, brain: RiskyBrain) -> None:
    base = {"conversation_id": "voice2"}
    wrong_type = await client.post(
        "/api/chat/send-audio", data=base, files={"audio": ("x.txt", b"hi", "text/plain")}
    )
    assert wrong_type.status_code == 415
    silent = await client.post(
        "/api/chat/send-audio", data=base, files={"audio": ("x.webm", b"silence", "audio/webm")}
    )
    assert silent.status_code == 422
    bad_conv = await client.post(
        "/api/chat/send-audio",
        data={"conversation_id": "../x"},
        files={"audio": ("x.webm", b"a", "audio/webm")},
    )
    assert bad_conv.status_code == 422
