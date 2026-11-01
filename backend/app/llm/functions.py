"""LLM tasks used by the graph. Nodes and tests depend on these, not on a vendor (D-014)."""

from functools import lru_cache
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import provider
from app.schemas.extraction import Extraction, IntentResult
from app.schemas.pricing import Catalog

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
INTENT_PROMPT = "intent_v1"
EXTRACT_PROMPT = "extract_v1"


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def wrap_inquiry(text: str) -> str:
    """Delimit customer text as data (D-015). Tags inside the text are removed so it can't close
    the block early and smuggle in instructions."""
    cleaned = text.replace("<inquiry>", "").replace("</inquiry>", "").strip()
    return f"<inquiry>\n{cleaned}\n</inquiry>"


def spec_vocabulary(catalog: Catalog) -> str:
    """Spec names the catalog requires, with option words where a spec has fixed options."""
    options: dict[str, set[str]] = {}
    for item in catalog.items:
        for spec in item.required_specs:
            options.setdefault(spec, set()).update(item.spec_surcharges.get(spec, {}))
    lines = []
    for spec in sorted(options):
        allowed = sorted(options[spec])
        lines.append(f"- {spec}" + (f": one of {', '.join(allowed)}" if allowed else ""))
    return "\n".join(lines)


async def classify_intent(text: str) -> IntentResult:
    messages = [SystemMessage(load_prompt(INTENT_PROMPT)), HumanMessage(wrap_inquiry(text))]
    return await provider.structured(IntentResult).ainvoke(messages)


async def extract(text: str, *, catalog: Catalog) -> Extraction:
    system = load_prompt(EXTRACT_PROMPT).replace("{{VOCABULARY}}", spec_vocabulary(catalog))
    messages = [SystemMessage(system), HumanMessage(wrap_inquiry(text))]
    return await provider.structured(Extraction).ainvoke(messages)
