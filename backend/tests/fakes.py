"""A deterministic stand-in for the LLM functions, used by graph and API tests (D-014)."""

from app.agent.deps import Deps
from app.config import Settings
from app.db.repo import Repo
from app.schemas.extraction import ExtractedItem, Extraction, IntentResult, RiskResult, Spec
from app.schemas.pricing import Catalog
from tests.golden import load_golden

CANCEL_WORDS = ("cancel", "rehne do", "nahi chahiye")
QUOTE_HINTS = ("quote", "price", "rate", "need", "chahiye", "sizes", "size", "pcs")


def tee(qty: int, *, sizes: bool = True, color: str = "black") -> Extraction:
    specs = [Spec(name="print_type", value="screen"), Spec(name="placement", value="front")]
    if sizes:
        specs.append(Spec(name="size_mix", value=f"M:{qty}"))
    return Extraction(
        items=[ExtractedItem(item_text=f"{color} round-neck t-shirt", quantity=qty, specs=specs)]
    )


class FakeBrain:
    """Intent by keywords; extraction from a registry keyed by the exact text the graph sends
    (all messages of the request joined by newlines), falling back to the golden set."""

    def __init__(self) -> None:
        self.extractions: dict[str, Extraction] = {
            case["input"]: Extraction.model_validate(case["ideal_extraction"])
            for case in load_golden()
        }
        self.intent_calls: list[str] = []
        self.extract_calls: list[str] = []

    def when(self, text: str, extraction: Extraction) -> "FakeBrain":
        self.extractions[text] = extraction
        return self

    async def classify_intent(self, text: str) -> IntentResult:
        self.intent_calls.append(text)
        lowered = text.lower()
        if any(w in lowered for w in CANCEL_WORDS):
            return IntentResult(intent="cancel", reason="fake")
        known = any(text in key for key in self.extractions)
        if known or any(ch.isdigit() for ch in text) or any(w in lowered for w in QUOTE_HINTS):
            return IntentResult(intent="new_quote", reason="fake")
        return IntentResult(intent="other", reason="fake")

    async def extract(self, text: str) -> Extraction:
        self.extract_calls.append(text)
        if text not in self.extractions:
            raise AssertionError(f"FakeBrain has no extraction registered for {text!r}")
        return self.extractions[text]

    def deps_factory(self, catalog: Catalog, repo: Repo, settings: Settings) -> Deps:
        return Deps(
            catalog=catalog,
            repo=repo,
            settings=settings,
            classify_intent=self.classify_intent,
            extract=self.extract,
            pdf_dir=settings.storage_dir / "quotes",
        )


class RiskyBrain(FakeBrain):
    """FakeBrain plus an LLM-style risk check and a transcriber, for Phase 10 tests."""

    def __init__(self) -> None:
        super().__init__()
        self.risk_calls: list[str] = []
        self.transcripts: dict[bytes, str] = {}
        self.fail_risk = False

    async def classify_risk(self, text: str) -> RiskResult:
        self.risk_calls.append(text)
        if self.fail_risk:
            raise TimeoutError("risk model unavailable")
        if "you idiot" in text.lower():
            return RiskResult(risk="abuse", reason="fake")
        if "pretend you are the owner" in text.lower():
            return RiskResult(risk="injection", reason="fake")
        return RiskResult(risk="none", reason="fake")

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        return self.transcripts.get(audio, "")

    def deps_factory(self, catalog: Catalog, repo: Repo, settings: Settings) -> Deps:
        deps = super().deps_factory(catalog, repo, settings)
        deps.classify_risk = self.classify_risk
        deps.transcribe = self.transcribe
        return deps
