"""Dispatch and 48-hour follow-ups (Phase 11, D-013)."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.agent.runtime import REPLY_ACCEPTED, Runtime
from app.config import Settings
from app.db.repo import Repo
from app.main import create_app
from app.schemas.decision import Approve
from app.services.followups import FollowupService, job_id, make_scheduler
from app.services.outbound import InAppOutbound
from tests.fakes import FakeBrain

HOODIES = "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10"
CUSTOMER = {"name": "Ravi Kumar", "state": "CG"}


@pytest.fixture
def runtime(app: FastAPI) -> Runtime:
    return app.state.runtime


@pytest.fixture
def followups(app: FastAPI) -> FollowupService:
    return app.state.followups


async def send_quote(runtime: Runtime, conv: str = "f1") -> str:
    started = await runtime.handle_message(conv, HOODIES, customer=CUSTOMER)
    await runtime.decide(started.quote_id, Approve(action="approve"))
    return started.quote_id


async def kinds(repo: Repo, quote_id: str) -> list[str]:
    return [e.kind for e in await repo.get_events(quote_id)]


async def test_dispatch_sends_pdf_message_and_schedules_followup(
    runtime: Runtime, repo: Repo, followups: FollowupService, client: httpx.AsyncClient
) -> None:
    before = datetime.now(UTC)
    quote_id = await send_quote(runtime)
    quote = await repo.get_quote(quote_id)
    assert quote.status == "sent" and quote.sent_at is not None

    messages = (await client.get("/api/conversations/f1/messages")).json()
    last = messages[-1]
    assert last["kind"] == "quote"
    assert last["pdf_url"] == f"/files/quotes/{quote_id}/r1.pdf"
    assert "Reply YES" in last["text"]

    when = followups.scheduled_for(quote_id)
    assert when is not None
    assert timedelta(hours=47.9) < when - before < timedelta(hours=48.1)


async def test_followup_is_sent_once(
    runtime: Runtime, repo: Repo, followups: FollowupService
) -> None:
    quote_id = await send_quote(runtime)
    assert await followups.run_followup(quote_id) is True
    assert await followups.run_followup(quote_id) is False  # status is followed_up now

    quote = await repo.get_quote(quote_id)
    assert quote.status == "followed_up"
    nudges = [m for m in await repo.list_messages("f1") if m.text.startswith("Hi Ravi")]
    assert len(nudges) == 1
    assert nudges[0].kind == "quote"


async def test_customer_reply_cancels_followup(
    runtime: Runtime, repo: Repo, followups: FollowupService, brain: FakeBrain
) -> None:
    quote_id = await send_quote(runtime)
    brain.when("can you do 60 instead?", brain.extractions[HOODIES])
    await runtime.handle_message("f1", "can you do 60 instead?", customer=CUSTOMER)

    assert followups.scheduled_for(quote_id) is None
    assert "followup_cancelled" in await kinds(repo, quote_id)
    assert await followups.run_followup(quote_id) is False  # even if a stale job fired


@pytest.mark.parametrize("text", ["YES", "haan ji", "ok confirm.", "Yes please!"])
async def test_yes_accepts_the_quote(
    text: str, runtime: Runtime, repo: Repo, followups: FollowupService
) -> None:
    quote_id = await send_quote(runtime)
    result = await runtime.handle_message("f1", text, customer=CUSTOMER)
    quote = await repo.get_quote(quote_id)
    assert quote.status == "accepted"
    assert result.reply == REPLY_ACCEPTED.format(number=quote.number)
    assert followups.scheduled_for(quote_id) is None


async def test_yes_with_changes_is_not_acceptance(
    runtime: Runtime, repo: Repo, brain: FakeBrain
) -> None:
    quote_id = await send_quote(runtime)
    brain.when("yes but make it 60", brain.extractions[HOODIES])
    await runtime.handle_message("f1", "yes but make it 60", customer=CUSTOMER)
    assert (await repo.get_quote(quote_id)).status != "accepted"


async def test_cancel_after_sending_cancels_followup(
    runtime: Runtime, repo: Repo, followups: FollowupService
) -> None:
    quote_id = await send_quote(runtime)
    await runtime.handle_message("f1", "please cancel the order", customer=CUSTOMER)
    assert (await repo.get_quote(quote_id)).status == "cancelled"
    assert followups.scheduled_for(quote_id) is None


async def test_jobs_survive_a_restart(settings: Settings, repo: Repo) -> None:
    first = make_scheduler(settings)
    first.start()
    FollowupService(repo, InAppOutbound(repo), first, settings).schedule("q_restart")
    first.shutdown(wait=False)

    second = make_scheduler(settings)
    second.start()
    try:
        assert second.get_job(job_id("q_restart")) is not None
    finally:
        second.shutdown(wait=False)


async def test_timer_fires_for_real(tmp_path: Path) -> None:
    settings = Settings(
        storage_dir=tmp_path / "s", followup_hours=1.5 / 3600, _env_file=None
    )  # ~1.5 s
    brain = FakeBrain()
    app = create_app(settings, deps_factory=brain.deps_factory)
    async with app.router.lifespan_context(app):
        quote_id = await send_quote(app.state.runtime, conv="timer")
        for _ in range(40):
            if (await app.state.repo.get_quote(quote_id)).status == "followed_up":
                break
            await asyncio.sleep(0.2)
        assert (await app.state.repo.get_quote(quote_id)).status == "followed_up"
