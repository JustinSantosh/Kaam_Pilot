# Phase 12: Evals & observability

- **Status:** Not started
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
- [ ] Label dataset (expected totals computed with the Phase 02 engine, then hand-checked).
- [ ] Runner calls the real graph nodes (not a copy of the logic), with replay mode for CI.
- [ ] Markdown report per run; summary table in README.
- [ ] LangSmith: env-based tracing, run metadata (`conversation_id`, `quote_id`, prompt version).
- [ ] Compare 2 models; record the winner in a new decision entry if it changes D-014's choice.
- [ ] Error analysis: top 5 failure patterns → prompt or matcher fixes → re-run.

## Exit criteria
- `run_evals --mode replay` runs in CI in under a minute and fails if total-match % drops below a set threshold.
- Report published with all metrics; at least one prompt/matcher improvement shown before/after.

## Risks / open questions
- Labeling effort is the bottleneck; label in batches of 10 and keep adding cases from real demo failures.

## Notes / changelog
- 2026-10-31: phase file created.
