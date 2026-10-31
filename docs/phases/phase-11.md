# Phase 11: Dispatch & follow-ups

- **Status:** Not started
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
- [ ] Scheduler started/stopped in FastAPI lifespan; job store on `kaampilot.db`.
- [ ] Follow-up job, cancel hooks, idempotency checks.
- [ ] Demo setting: `KP_FOLLOWUP_HOURS=0.02` (~1 min).
- [ ] "YES" acceptance rule → `status=accepted`, cancel follow-up, notify owner in the inbox.

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
