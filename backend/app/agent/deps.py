"""What the graph's nodes depend on. Tests swap the LLM functions for fakes (D-014)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.db.repo import Repo
from app.llm import functions as llm
from app.llm.demo import DemoBrain
from app.schemas.extraction import Extraction, IntentResult, RiskResult
from app.schemas.pricing import Catalog
from app.services.followups import FollowupService

ClassifyIntent = Callable[[str], Awaitable[IntentResult]]
Extract = Callable[[str], Awaitable[Extraction]]
ClassifyRisk = Callable[[str], Awaitable[RiskResult]]
Transcribe = Callable[[bytes, str], Awaitable[str]]

DEMO_MODEL = "demo"


@dataclass
class Deps:
    catalog: Catalog
    repo: Repo
    settings: Settings
    classify_intent: ClassifyIntent
    extract: Extract
    classify_risk: ClassifyRisk | None = None  # None → rules-only guardrail (D-015)
    transcribe: Transcribe | None = None  # None → voice notes are refused
    followups: FollowupService | None = None  # set at startup (Phase 11)
    pdf_dir: Path = field(default=Path("storage/quotes"))


def default_deps(catalog: Catalog, repo: Repo, settings: Settings) -> Deps:
    if settings.llm_model == DEMO_MODEL:  # offline stand-in, no API key needed (D-022)
        brain = DemoBrain()
        return Deps(
            catalog=catalog,
            repo=repo,
            settings=settings,
            classify_intent=brain.classify_intent,
            extract=brain.extract,
            transcribe=brain.transcribe,
            pdf_dir=settings.storage_dir / "quotes",
        )

    async def extract(text: str) -> Extraction:
        return await llm.extract(text, catalog=catalog)

    return Deps(
        catalog=catalog,
        repo=repo,
        settings=settings,
        classify_intent=llm.classify_intent,
        extract=extract,
        classify_risk=llm.classify_risk,
        transcribe=llm.transcribe,
        pdf_dir=settings.storage_dir / "quotes",
    )
