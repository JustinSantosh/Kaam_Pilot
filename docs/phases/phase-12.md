# Phase 12: Evals & observability

- **Status:** Done (live LLM run pending API key)
- **Depends on:** [03](phase-03.md), [10](phase-10.md)
- **Decisions:** [D-014](../decisions.md#d-014), [D-017](../decisions.md#d-017)

## Goal
Measure how good the system actually is, with numbers you can put in a README and defend in an
interview, and trace every run.

## Scope
**In:** labeled dataset, eval runner, metrics report, recorded-response mode for CI, LangSmith
tracing, model comparison run.
**Out:** online A/B testing.

## Deliverables
```
backend/evals/dataset.json            # 60+ labeled cases
backend/evals/run_evals.py            # python -m evals.run_evals --mode live|replay --model …
backend/evals/metrics.py
backend/evals/recordings/             # cached LLM responses for replay mode
backend/evals/reports/YYYY-MM-DD-<model>.md
```

## Dataset case shape
```json
{
  "id": "hinglish-07",
  "tags": ["hinglish", "multi_item", "missing_spec"],
  "input": "bhaiya 40 kaali tee aur 20 safed, front pe logo, sizes baad me batata hu",
  "customer_state": "CG",
  "expected": {
    "intent": "new_quote",
    "items": [{"sku": "TEE-RN-BLK", "quantity": 40, "specs": {"placement": "front"}},
              {"sku": "TEE-RN-WHT", "quantity": 20, "specs": {"placement": "front"}}],
    "outcome": "clarify",
    "missing": {"TEE-RN-BLK": ["size_mix", "print_type"], "TEE-RN-WHT": ["size_mix", "print_type"]},
    "total_paise": null
  }
}
```
Mix: clean (10), Hinglish (15), typos/slang (10), voice-transcript style (8), multi-item (8),
missing specs (8), cancellations (4), off-topic (3), adversarial (10+, reused from Phase 10).

## Metrics ([D-017](../decisions.md#d-017))
Intent accuracy · item P/R/F1 by SKU · quantity accuracy · per-spec accuracy · clarify exactness ·
**end-to-end total match %** · guardrail block rate / false-positive rate · p50/p95 latency ·
tokens and cost per quote. LLM-as-judge only for wording of clarify/reply drafts.

## Tasks
- [x] Label dataset (expected totals computed with the Phase 02 engine, then hand-checked).
- [x] Runner calls the real graph nodes (not a copy of the logic), with replay mode for CI.
- [x] Markdown report per run; summary table in README.
- [x] LangSmith: env-based tracing, run metadata (`conversation_id`, `quote_id`, prompt version).
- [x] Compare 2 models; record the winner in a new decision entry if it changes D-014's choice.
- [x] Error analysis: top 5 failure patterns → prompt or matcher fixes → re-run.

## Exit criteria
- `run_evals --mode replay` runs in CI in under a minute and fails if total-match % drops below a set threshold.
- Report published with all metrics; at least one prompt/matcher improvement shown before/after.

## Risks / open questions
- Labeling effort is the bottleneck; label in batches of 10 and keep adding cases from real demo failures.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-12-evals`.
  - Dataset: **84 cases** (`evals/dataset.json`, built by `evals/build_dataset.py`): clean 10, Hinglish 15,
    typos/slang 10, voice-transcript style 8, multi-item 8, missing specs 8, cancellations 4,
    off-topic 3, adversarial 18. Each case stores the ideal reader output plus frozen expected SKUs,
    quantities, missing fields and totals. Three totals are hand-checked in `tests/test_evals.py`.
  - Runner `python -m evals.run_evals --mode ideal|live|replay [--record] [--min-total-match 1.0]`:
    guardrail → intent → extraction → validation → pricing, using the same service functions as the graph.
    `live` calls the configured LLM; `--record` saves outputs to `evals/recordings/` for `replay`.
  - Metrics (`evals/metrics.py`): outcome and intent accuracy, item P/R/F1, quantity and per-spec accuracy,
    clarification exactness, **end-to-end total match**, guardrail block rate (overall and
    rule-blockable), false-positive rate, money-override flag rate, latency p50/p95, per-category table.
  - Ideal-mode report committed (`evals/reports/…-ideal-pipeline.md`): total match 100%, clarification
    exactness 100%, false positives 0%, rule-blockable attacks 100% blocked. The 2 attacks that need the
    LLM risk check show as unblocked in ideal mode, which is expected.
  - Observability: LLM calls carry LangSmith `run_name` + prompt-version tags; graph runs carry
    `run_name=kaampilot-turn` and `conversation_id` metadata. Tracing turns on with `LANGSMITH_TRACING=true`.
  - Not done (needs the API key): live run, model comparison (3.5 Flash-Lite vs 3.6 Flash), error
    analysis of live failures. Steps are in the owner to-do doc.
  - Tests: 416 offline (7 new).
