"""Match a customer's item description to catalog SKUs. Deterministic; no LLM (D-004)."""

import re
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz

from app.schemas.pricing import Catalog, CatalogItem

MATCH_MIN = 80  # best score needed to accept a match
AMBIGUITY_MARGIN = 8  # the runner-up must trail by more than this
CANDIDATE_MIN = 55  # below this an item is not even offered as a candidate
MAX_CANDIDATES = 3

_TSHIRT = re.compile(r"\bt[\s-]?shirts?\b|\btees?\b")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    """Lowercase, unify t-shirt spellings, drop punctuation and simple plural 's'."""
    text = _TSHIRT.sub(" tshirt ", text.lower())
    tokens = _NON_ALNUM.sub(" ", text).split()
    return " ".join(
        t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t for t in tokens
    )


@dataclass(frozen=True)
class Candidate:
    sku: str
    name: str
    score: float


@dataclass(frozen=True)
class MatchResult:
    status: Literal["matched", "ambiguous", "none"]
    sku: str | None
    candidates: tuple[Candidate, ...]


def _phrases(item: CatalogItem) -> list[str]:
    return [normalize(p) for p in (item.name, item.sku, *item.aliases)]


def _score(query: str, item: CatalogItem) -> float:
    return max(fuzz.token_set_ratio(query, phrase) for phrase in _phrases(item))


def match(item_text: str, catalog: Catalog) -> MatchResult:
    query = normalize(item_text)
    if not query:
        return MatchResult("none", None, ())

    exact = [i for i in catalog.items if query in _phrases(i)]
    if len(exact) == 1:
        hit = exact[0]
        return MatchResult("matched", hit.sku, (Candidate(hit.sku, hit.name, 100.0),))

    scored = sorted(
        (Candidate(i.sku, i.name, _score(query, i)) for i in catalog.items),
        key=lambda c: c.score,
        reverse=True,
    )
    best = scored[0]
    if best.score < CANDIDATE_MIN:
        return MatchResult("none", None, ())

    runner_up = scored[1].score if len(scored) > 1 else 0.0
    if best.score >= MATCH_MIN and best.score - runner_up > AMBIGUITY_MARGIN:
        return MatchResult("matched", best.sku, (best,))

    close = tuple(c for c in scored if c.score >= CANDIDATE_MIN)[:MAX_CANDIDATES]
    return MatchResult("ambiguous", None, close)
