# Phase 03: Schemas & LLM extraction

- **Status:** Done, except choosing the model and running the live golden test (needs an API key)
- **Depends on:** [02](phase-02.md)
- **Decisions:** [D-002](../decisions.md#d-002), [D-003](../decisions.md#d-003), [D-004](../decisions.md#d-004), [D-014](../decisions.md#d-014), [D-015](../decisions.md#d-015), [D-019](../decisions.md#d-019)

## Goal
Turn a messy inquiry into a validated `Extraction`, map it to catalog SKUs, and decide, in code,
whether it's complete enough to price.

## Scope
**In:** extraction/intent schemas, LLM provider wrapper, intent + extraction prompts, SKU matcher,
completeness validator, golden-set tests.
**Out:** wiring into the graph (Phase 04), guardrails and voice (Phase 10).

## Deliverables
```
backend/app/schemas/extraction.py   # ExtractedItem, Extraction, IntentResult
backend/app/llm/provider.py         # get_model(), structured(schema)
backend/app/llm/prompts/intent_v1.md
backend/app/llm/prompts/extract_v1.md
backend/app/llm/functions.py        # classify_intent(text), extract(text)
backend/app/services/matcher.py     # match(item_text, specs) → MatchResult
backend/app/services/validator.py   # validate(extraction) → ValidationResult (+ quantity from dimensions)
backend/app/services/clarify.py     # clarify_message(result) → customer-facing questions
backend/tests/test_matcher.py
backend/tests/test_validator.py
backend/tests/test_clarify.py
backend/tests/test_llm_functions.py # LLM replaced at provider.structured; prompt + schema guards
backend/tests/golden/inquiries.json # 10 cases: input, ideal extraction, expected SKUs/qty/outcome
backend/tests/test_extract_golden.py  # marked @pytest.mark.llm (opt-in, live; skipped without KP_LLM_MODEL)
```

## Design
- **Intent:** `new_quote | cancel | other`. No `clarify` here ([D-004](../decisions.md#d-004)).
- **Extraction prompt rules:** copy quantities exactly; `None` if not stated; normalize Hinglish spec
  words to English keys (`kaala → black`); never invent; no prices. Customer text goes inside
  `<inquiry>…</inquiry>` delimiters.
- **Matcher:** normalize text → exact alias hit → fuzzy score (`rapidfuzz`) over name+aliases,
  boosted by spec agreement (e.g. color). Returns `matched | ambiguous(top-3) | none`.
  Thresholds are constants with tests.
- **Validator** (per item): SKU matched? quantity present and ≥ MOQ? every `required_specs` key
  present? Output `ValidationResult{complete, items:[{sku, missing:[...], issues:[...]}]}`.
- **Clarify text:** templated from `ValidationResult` (e.g. "For the black tees, which sizes and how
  many of each?"). The LLM may optionally polish the wording, but not change its content.

## Tasks
- [ ] Choose a current small model with good structured output; record the choice in decisions.md as a new entry.
      **Partly done:** [D-020](../decisions.md#d-020) proposes Gemini 3.5 Flash-Lite; confirm after a live eval run.
      Provider extras are ready: `pip install -e ".[openai]"`
      (or `google`, `anthropic`), then set `KP_LLM_MODEL` and the key in `backend/.env`.
- [x] `structured(schema)` = `get_model().with_structured_output(schema)`, retried up to 3 attempts on
      parse/validation errors.
- [x] Prompts with examples, including Hinglish and multi-item. The extraction prompt is given the catalog's spec
      vocabulary and option words, built from `catalog.json`.
- [x] Matcher + tests (exact, alias, typo, ambiguous, none).
- [x] Validator + tests (missing qty, below MOQ, missing spec, invalid option, unmatched, ambiguous).
- [x] Clarify message builder + tests.
- [x] Golden set of 10 inquiries. Offline: each ideal extraction is validated and, when complete, priced.
      Live: `pytest -m llm`.

## Exit criteria
- Unit tests for matcher/validator pass without network.
- `pytest -m llm` passes on 10 golden inquiries (or ≥9 with failures written down).
- An ambiguous request ("t-shirt" with black and white SKUs) produces `ambiguous`, which leads to a clarify question.

## Risks / open questions
- Size-mix parsing ("10 M, 15 L, baaki XL") may need a dedicated sub-schema `size_mix: dict[str,int]`.
  Decide after the golden runs.
- Units (sq ft, running ft) for carpentry/fabrication; the matcher must respect `unit`.

- Colour words for products we don't stock ("red t-shirt") come back as `ambiguous` between the
  stocked colours rather than `none`. Acceptable: the customer is asked which one they mean.
- Live golden test not yet run (no key). Exit criterion "≥9/10 pass live" is still open.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-10-31: implemented on branch `phase-03-extraction`. Changes from the original design:
  - `ExtractedItem.specs` is a list of `{name, value}` pairs instead of a dict, because strict
    JSON-schema modes reject free-form object keys.
  - Quantity for sqft/rft items is computed **in code** from `width_ft`/`height_ft`/`length_rft`
    ([D-019](../decisions.md#d-019)); the prompt tells the LLM to count pieces only.
  - The live golden test is skipped automatically when `KP_LLM_MODEL` is unset.
  - Tests: 311 offline (60 new), plus 10 live tests behind `-m llm`. `ruff` clean.
