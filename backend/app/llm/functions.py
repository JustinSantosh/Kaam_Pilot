"""LLM tasks used by the graph. Nodes and tests depend on these, not on a vendor (D-014)."""

import base64
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llm import provider
from app.schemas.extraction import Extraction, IntentResult, RiskResult
from app.schemas.pricing import Catalog

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
INTENT_PROMPT = "intent_v1"
EXTRACT_PROMPT = "extract_v1"
GUARDRAIL_PROMPT = "guardrail_v1"
TRANSCRIBE_PROMPT = "transcribe_v1"


def _trace(prompt: str) -> RunnableConfig:
    """LangSmith run name + prompt-version tag (tracing is on when LANGSMITH_TRACING=true)."""
    return {"run_name": prompt.rsplit("_", 1)[0], "tags": [prompt]}


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
    return await provider.structured(IntentResult).ainvoke(messages, config=_trace(INTENT_PROMPT))


async def extract(text: str, *, catalog: Catalog) -> Extraction:
    system = load_prompt(EXTRACT_PROMPT).replace("{{VOCABULARY}}", spec_vocabulary(catalog))
    messages = [SystemMessage(system), HumanMessage(wrap_inquiry(text))]
    return await provider.structured(Extraction).ainvoke(messages, config=_trace(EXTRACT_PROMPT))


async def classify_risk(text: str) -> RiskResult:
    messages = [SystemMessage(load_prompt(GUARDRAIL_PROMPT)), HumanMessage(wrap_inquiry(text))]
    return await provider.structured(RiskResult).ainvoke(messages, config=_trace(GUARDRAIL_PROMPT))


async def transcribe(audio: bytes, mime_type: str) -> str:
    """Speech to text with the configured multimodal model (Gemini accepts audio directly).

    The transcript is treated exactly like typed text afterwards: guardrail, intent, extraction.
    """
    message = HumanMessage(
        content=[
            {"type": "text", "text": load_prompt(TRANSCRIBE_PROMPT)},
            {
                "type": "audio",
                "base64": base64.b64encode(audio).decode("ascii"),
                "mime_type": mime_type,
            },
        ]
    )
    result = await provider.get_model().ainvoke([message], config=_trace(TRANSCRIBE_PROMPT))
    return str(result.text if hasattr(result, "text") else result.content).strip()
