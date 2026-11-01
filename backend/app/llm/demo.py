"""Offline stand-in for the LLM, enabled with KP_LLM_MODEL=demo (D-022).

It knows the preset demo scenarios exactly and handles simple free text with keyword rules, so
the whole app can be clicked through without an API key. It is not a model and makes no claim
to understand arbitrary messages; real extraction quality comes from the configured LLM.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from app.schemas.extraction import ExtractedItem, Extraction, IntentResult, Spec

SCENARIOS_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_scenarios.json"

CANCEL_WORDS = ("cancel", "rehne do", "nahi chahiye", "don't need")
QUOTE_WORDS = (
    "quote", "price", "rate", "need", "chahiye", "size", "pcs", "tee", "t-shirt", "tshirt",
    "hoodie", "polo", "gate", "railing", "wardrobe", "almirah", "kitchen", "banner", "flex",
)  # fmt: skip
SIZE_PAIR = re.compile(r"\b(XXS|XS|S|M|L|XL|XXL|XXXL)\s*[:\-]?\s*(\d+)\b", re.I)
NUMBER = re.compile(r"\b(\d+)\b")
SPEC_WORDS = {
    "print_type": {
        "screen": "screen", "dtf": "dtf", "embroidery": "embroidery", "kadhai": "embroidery",
        "embroidered": "embroidery",
    },
    "placement": {
        "front": "front", "aage": "front", "back": "back", "peeche": "back", "chest": "chest",
        "sleeve": "sleeve",
    },
}  # fmt: skip
COLOURS = {"black": "black", "kaali": "black", "kaala": "black", "white": "white",
           "safed": "white", "navy": "navy"}  # fmt: skip
PRODUCTS = ("t-shirt", "tshirt", "tee", "hoodie", "polo", "gate", "railing", "wardrobe",
            "almirah", "kitchen", "banner", "flex", "blazer")  # fmt: skip


@lru_cache
def scenarios() -> list[dict]:
    return json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))


@lru_cache
def _known() -> dict[str, Extraction]:
    known: dict[str, Extraction] = {}
    for sc in scenarios():
        known[sc["message"]] = Extraction.model_validate(sc["extraction"])
        if follow := sc.get("follow_up"):
            joined = f"{sc['message']}\n{follow['message']}"
            known[joined] = Extraction.model_validate(follow["extraction"])
    return known


def _heuristic(text: str) -> Extraction:
    lowered = text.lower()
    product = next((p for p in PRODUCTS if p in lowered), None)
    if product is None:
        return Extraction(items=[])
    sizes = SIZE_PAIR.findall(text)
    rest = SIZE_PAIR.sub(" ", text)
    numbers = [int(n) for n in NUMBER.findall(rest)]
    quantity = numbers[0] if numbers else (sum(int(n) for _, n in sizes) or None)
    specs = [
        Spec(name=name, value=value)
        for name, words in SPEC_WORDS.items()
        for word, value in words.items()
        if re.search(rf"\b{word}\b", lowered)
    ]
    specs = list({s.name: s for s in specs}.values())  # first match per spec
    if sizes:
        specs.append(Spec(name="size_mix", value=", ".join(f"{s.upper()}:{n}" for s, n in sizes)))
    colour = next((c for w, c in COLOURS.items() if re.search(rf"\b{w}\b", lowered)), "")
    return Extraction(
        items=[
            ExtractedItem(item_text=f"{colour} {product}".strip(), quantity=quantity, specs=specs)
        ]
    )


class DemoBrain:
    async def classify_intent(self, text: str) -> IntentResult:
        lowered = text.lower()
        if any(w in lowered for w in CANCEL_WORDS):
            return IntentResult(intent="cancel", reason="demo: cancel keyword")
        known = _known().get(text)
        if known is not None and not known.items:
            return IntentResult(intent="other", reason="demo: preset without products")
        if known or any(w in lowered for w in QUOTE_WORDS) or NUMBER.search(text):
            return IntentResult(intent="new_quote", reason="demo: product or quantity mentioned")
        return IntentResult(intent="other", reason="demo: no product or quantity")

    async def extract(self, text: str) -> Extraction:
        return _known().get(text) or _heuristic(text)
