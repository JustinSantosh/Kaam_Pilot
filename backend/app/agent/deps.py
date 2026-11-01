"""What the graph's nodes depend on. Tests swap the LLM functions for fakes (D-014)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.db.repo import Repo
from app.llm import functions as llm
from app.llm.demo import DemoBrain
from app.schemas.extraction import Extraction, IntentResult
from app.schemas.pricing import Catalog

ClassifyIntent = Callable[[str], Awaitable[IntentResult]]
Extract = Callable[[str], Awaitable[Extraction]]

DEMO_MODEL = "demo"


@dataclass
class Deps:
    catalog: Catalog
    repo: Repo
    settings: Settings
    classify_intent: ClassifyIntent
    extract: Extract
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
        pdf_dir=settings.storage_dir / "quotes",
    )
