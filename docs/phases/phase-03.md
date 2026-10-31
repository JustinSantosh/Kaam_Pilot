# Phase 03: Schemas & LLM extraction

- **Status:** Not started
- **Depends on:** [02](phase-02.md)
- **Decisions:** [D-002](../decisions.md#d-002), [D-003](../decisions.md#d-003), [D-004](../decisions.md#d-004), [D-014](../decisions.md#d-014)

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
backend/app/services/validator.py   # validate(extraction) → ValidationResult
backend/tests/test_matcher.py
backend/tests/test_validator.py
backend/tests/golden/inquiries.json # 10 cases with expected extraction
backend/tests/test_extract_golden.py  # marked @pytest.mark.llm (opt-in, live)
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
- [ ] `structured(schema)` = `get_model().with_structured_output(schema)`, with retry on validation error (max 2).
- [ ] Write the prompts with 3–4 few-shot examples, including one Hinglish and one multi-item.
- [ ] Matcher + tests (exact, alias, typo, ambiguous, none).
- [ ] Validator + tests (missing qty, below MOQ, missing spec, unmatched SKU).
- [ ] Golden set of 10 inquiries; live test runs only with `-m llm`.

## Exit criteria
- Unit tests for matcher/validator pass without network.
- `pytest -m llm` passes on 10 golden inquiries (or ≥9 with failures written down).
- An ambiguous request ("t-shirt" with black and white SKUs) produces `ambiguous`, which leads to a clarify question.

## Risks / open questions
- Size-mix parsing ("10 M, 15 L, baaki XL") may need a dedicated sub-schema `size_mix: dict[str,int]`.
  Decide after the golden runs.
- Units (sq ft, running ft) for carpentry/fabrication; the matcher must respect `unit`.

## Notes / changelog
- 2026-10-31: phase file created.
