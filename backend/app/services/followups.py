"""48-hour follow-ups (D-013). Jobs live in a persistent SQLAlchemy job store, so they survive a
restart; every run re-checks the quote, so a follow-up is sent at most once and never after the
customer replied, accepted or cancelled.
"""

from datetime import UTC, datetime, timedelta

from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.db.repo import Repo
from app.services.money import paise_to_display
from app.services.outbound import Outbound

JOBS_TABLE = "apscheduler_jobs"

NUDGE = (
    "Hi{name}, just checking in on quote {number} ({total}). Reply YES to confirm the order, or "
    "tell us what you'd like to change."
)

_service: "FollowupService | None" = None  # set at startup; jobs are stored by reference


def job_id(quote_id: str) -> str:
    return f"followup:{quote_id}"


def make_scheduler(settings: Settings) -> AsyncIOScheduler:
    url = f"sqlite:///{(settings.storage_dir / 'kaampilot.db').as_posix()}"
    return AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=url, tablename=JOBS_TABLE)},
        job_defaults={"misfire_grace_time": 24 * 3600, "coalesce": True},
        timezone="UTC",
    )


async def run_followup_job(quote_id: str) -> None:
    """Entry point the scheduler stores by reference (must stay importable at module level)."""
    if _service is not None:
        await _service.run_followup(quote_id)


class FollowupService:
    def __init__(
        self, repo: Repo, outbound: Outbound, scheduler: AsyncIOScheduler, settings: Settings
    ) -> None:
        self.repo = repo
        self.outbound = outbound
        self.scheduler = scheduler
        self.settings = settings

    def activate(self) -> None:
        global _service
        _service = self

    def schedule(self, quote_id: str, *, now: datetime | None = None) -> datetime:
        when = (now or datetime.now(UTC)) + timedelta(hours=self.settings.followup_hours)
        self.scheduler.add_job(
            run_followup_job,
            "date",
            run_date=when,
            args=[quote_id],
            id=job_id(quote_id),
            replace_existing=True,  # idempotent: re-dispatch never creates a second job
        )
        return when

    def cancel(self, quote_id: str) -> bool:
        try:
            self.scheduler.remove_job(job_id(quote_id))
        except JobLookupError:
            return False
        return True

    def scheduled_for(self, quote_id: str) -> datetime | None:
        job = self.scheduler.get_job(job_id(quote_id))
        return job.next_run_time if job else None

    async def run_followup(self, quote_id: str) -> bool:
        quote = await self.repo.get_quote(quote_id)
        if quote is None or quote.status != "sent" or quote.sent_at is None:
            if quote is not None:
                await self.repo.add_event(quote_id, "followup_skipped", {"status": quote.status})
            return False
        last_reply = await self.repo.last_customer_message_at(quote.conversation_id)
        sent_at = quote.sent_at.replace(tzinfo=None)
        if last_reply is not None and last_reply.replace(tzinfo=None) > sent_at:
            await self.repo.add_event(quote_id, "followup_skipped", {"reason": "customer replied"})
            return False
        conv = await self.repo.get_conversation(quote.conversation_id)
        first_name = (conv.customer_name.split() or [""])[0] if conv else ""
        text = NUDGE.format(
            name=f" {first_name}" if first_name else "",
            number=quote.number,
            total=paise_to_display(quote.total_paise),
        )
        await self.outbound.send(quote.conversation_id, text, quote_id=quote_id, kind="quote")
        await self.repo.set_status(quote_id, "followed_up")
        return True
