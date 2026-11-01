# Phase 11: Dispatch & follow-ups

- **Status:** Done
- **Depends on:** [05](phase-05.md), [07](phase-07.md)
- **Decisions:** [D-010](../decisions.md#d-010), [D-013](../decisions.md#d-013)

## Goal
After approval, send the quote to the customer and reliably follow up once after 48 hours if they
haven't responded. Never twice, and never after they replied.

## Scope
**In:** real `dispatch` node, outbound message abstraction, APScheduler with persistent job store,
follow-up job, cancel rules, customer "accept" handling.
**Out:** real WhatsApp/SMS/email delivery (a stretch goal; the abstraction makes it pluggable).

## Deliverables
```
backend/app/services/outbound.py      # Outbound protocol + InAppOutbound (writes to conversation)
backend/app/services/scheduler.py     # AsyncIOScheduler + SQLAlchemyJobStore
backend/app/services/followups.py     # schedule_followup, cancel_followup, run_followup
backend/app/agent/nodes/dispatch.py
backend/tests/test_dispatch.py
backend/tests/test_followups.py
```

## Design
- `dispatch`: if `sent_at` is already set, do nothing ([D-010](../decisions.md#d-010)); otherwise send
  message + PDF link, set `status=sent`, `sent_at`, and schedule `followup:{quote_id}` at
  `now + KP_FOLLOWUP_HOURS` (`replace_existing=True`).
- `run_followup(quote_id)`: reload quote; only if `status == sent` and no customer message since
  `sent_at` → send nudge, `status=followed_up`. Otherwise no-op.
- Cancel the job on: customer message on the conversation, cancel intent, accept.
- Customer accept: intent `other` with an "accept" phrase is out of MVP scope; simple path: the
  dispatched message offers "Reply YES to confirm", and a YES reply is handled by a small rule before the graph.

## Tasks
- [x] Scheduler started/stopped in FastAPI lifespan; job store on `kaampilot.db`.
- [x] Follow-up job, cancel hooks, idempotency checks.
- [x] Demo setting: `KP_FOLLOWUP_HOURS=0.02` (~1 min).
- [x] "YES" acceptance rule → `status=accepted`, cancel follow-up, notify owner in the inbox.

## Exit criteria
- Approve → customer sees the quote + PDF link once, even if `dispatch` is retried.
- **Restart test:** schedule, recreate scheduler from the same job store → job still fires.
- Customer replies before the deadline → no follow-up sent.
- Follow-up fires exactly once.

## Risks / open questions
- Single-process assumption ([D-013](../decisions.md#d-013)): running multiple uvicorn workers would
  run duplicate schedulers. Document `--workers 1`.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-11-dispatch`.
  - `dispatch` renders the final PDF and moves the status `approved → sent` (with `sent_at`). The reply
    is a `kind="quote"` message, so the Customer Hub shows a "Download quotation PDF" card with the
    total incl. GST and "Reply YES to confirm". Idempotent: a quote with `sent_at` is never re-sent.
  - `services/followups.py`: `AsyncIOScheduler` + `SQLAlchemyJobStore` on `kaampilot.db`; job id
    `followup:{quote_id}` with `replace_existing`; the job function is stored by reference. Each run
    re-checks status and replies, so the nudge goes out at most once (`sent → followed_up`).
  - Cancelled on: any customer reply after sending, cancel intent, acceptance. A bare
    "YES / haan ji / ok confirm" sets `accepted` without running the graph; "yes but make it 60"
    goes through the graph as a change request.
  - `services/outbound.py`: `Outbound` protocol + `InAppOutbound`; a WhatsApp/SMS channel can plug in here.
  - Single scheduler per process: run uvicorn with `--workers 1` (D-013).
  - Verified in the browser: gate + railing for a Mumbai site → ₹1,16,796.40 incl. 18% IGST (checked
    by hand) → approved → PDF card in the chat.
  - Tests: 409 offline (11 new), including jobs surviving a restart and a real ~1.5 s timer firing.
