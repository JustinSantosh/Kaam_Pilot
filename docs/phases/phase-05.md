# Phase 05: Human-in-the-loop

- **Status:** Done
- **Depends on:** [04](phase-04.md)
- **Decisions:** [D-008](../decisions.md#d-008), [D-009](../decisions.md#d-009), [D-010](../decisions.md#d-010)

## Goal
The graph pauses at an approval boundary, survives restarts while paused, and resumes correctly for
approve, edit and reject, with no duplicated side effects.

## Scope
**In:** `hitl_pause` node with `interrupt()`, decision schema, routing after resume, edit → re-price
loop with revisions, `mark_rejected` node, pending-interrupt guard helper, `dispatch` stub.
**Out:** HTTP endpoints (Phase 07), real sending/scheduling (Phase 11), UI (Phase 09).

## Deliverables
```
backend/app/schemas/decision.py     # Decision = Approve | Edit | Reject (discriminated union)
backend/app/agent/nodes/hitl.py     # hitl_pause, apply_edits, mark_rejected
backend/app/agent/nodes/dispatch.py # stub: sets status=approved, records event
backend/app/agent/runtime.py        # start_or_continue(conv_id, input), resume(conv_id, decision), pending(conv_id)
backend/tests/test_hitl.py
```

## Design
```python
async def hitl_pause(state):
    # D-010: nothing above this line has side effects.
    decision = interrupt(build_review_payload(state))
    return {"decision": Decision.model_validate(decision).model_dump()}
```
- Status `awaiting_approval` is set in `render_pdf` (before the pause), not in `hitl_pause`.
- Routing after `hitl_pause`: `approve → dispatch`, `edit → apply_edits → price`, `reject → mark_rejected`.
- `apply_edits` validates edits against the catalog (SKU exists, qty ≥ MOQ). Invalid edits loop back
  to `hitl_pause` with an `errors` field in the payload instead of crashing.
- `price` bumps `revision` when called after an edit; old `quote_items` rows are kept.
- `runtime.pending(conv_id)`: `aget_state` → returns the interrupt payload if `state.tasks` has one ([D-008](../decisions.md#d-008)).

## Tasks
- [x] Decision discriminated union: `{"action": "approve"}`, `{"action": "reject", "reason"}`,
      `{"action": "edit", "edits": {items?, discount_paise?, discount_pct_bp?}}`.
- [x] `hitl_pause`, `apply_edits`, `mark_rejected`, `dispatch` stub.
- [x] `runtime.py` wraps `ainvoke` / `Command(resume=…)` and returns a normalized result
      (`awaiting_approval | needs_clarification | completed | rejected | busy`).
- [x] Customer message while pending → stored as a `quote_event` note; returns `busy`.

## Exit criteria
Tests (LLM mocked, real SQLite in `tmp_path`):
- run → paused with payload; `pending()` returns it;
- **restart**: new checkpointer instance → resume approve → `dispatch` ran once, status `approved`;
- edit qty 50→60 → revision 2, new totals, paused again; then approve;
- edit with discount → discount line present, tax computed on the discounted value;
- invalid edit (qty < MOQ) → paused again with errors, no new revision;
- reject → status `rejected`, reason saved;
- `quote_events` counts are exactly as expected (no duplicates from the replay) ([D-010](../decisions.md#d-010));
- new message while pending → `busy`, pending interrupt intact.

## Risks / open questions
- Concurrency: two owner clicks at once. Mitigate with a per-conversation `asyncio.Lock` in
  `runtime` (single process); record it in the decision log if it becomes a problem.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-05-hitl`.
  - Graph: `price → render_pdf → submit_for_review → hitl_pause`, then `approve → dispatch`,
    `edit → apply_edits → price` (or back to `hitl_pause` with `edit_errors`), and
    `reject → mark_rejected`. The quote status changes to `awaiting_approval` in
    `submit_for_review`, before the pause (D-010).
  - `schemas/decision.py`: `Approve | Reject | Edit`, with discriminator `action`. Edits are a full
    replacement line list (specs kept when omitted), a discount, or `remove_discount`; there's no total field (D-009).
  - `agent/runtime.py`: `handle_message` / `decide` / `pending`; per-conversation asyncio lock;
    `busy` + `customer_note` while pending (D-008); `StaleRevisionError`, `QuoteNotPendingError`.
  - The customer hears "being prepared" once (revision 1); owner edits don't message them.
  - Tests: 335 offline (10 new), including approve after a restart, exact event sequence (no replay
    duplicates), invalid edit, discount, and busy handling.
