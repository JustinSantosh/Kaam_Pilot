# Phase 07: API layer

- **Status:** Not started
- **Depends on:** [05](phase-05.md), [06](phase-06.md)
- **Decisions:** [D-007](../decisions.md#d-007), [D-008](../decisions.md#d-008), [D-011](../decisions.md#d-011), [D-016](../decisions.md#d-016)

## Goal
Expose the workflow over HTTP exactly as specified in [project.md §6](../project.md#6-api-contract),
so the frontend can be built against a stable contract.

## Scope
**In:** chat, conversation messages, inbox, quote detail, decision, file routes; request/response
models; error model; CORS; OpenAPI.
**Out:** auth (single-business demo; noted as a known limit in Phase 13), rate limiting.

## Deliverables
```
backend/app/schemas/api.py
backend/app/api/routes_chat.py        # POST /api/chat/send, GET /api/conversations/{id}/messages
backend/app/api/routes_business.py    # GET /api/business/inbox
backend/app/api/routes_quotes.py      # GET /api/quotes/{id}, POST /api/quotes/{id}/decision
backend/app/api/routes_files.py       # GET /files/quotes/...
backend/app/api/errors.py             # {"error": {"code", "message"}} + handlers
backend/tests/test_api_flow.py
```

## Tasks
- [ ] All routes `async def`, using `runtime.py` from Phase 05 (no graph logic in routes).
- [ ] Inbox and detail read from the **records DB**, never from checkpoints ([D-007](../decisions.md#d-007)).
- [ ] `messages?since=<id>` cursor for cheap polling ([D-016](../decisions.md#d-016)).
- [ ] Decision on a quote that isn't `awaiting_approval` → 409 `quote_not_pending`.
- [ ] Decision for a stale revision (client sends `revision`) → 409 `stale_revision`.
- [ ] Generate `openapi.json`; optionally generate TS types for the frontend (`openapi-typescript`).

## Exit criteria
`httpx` end-to-end test with mocked LLM:
1. `POST /chat/send` incomplete → `needs_clarification` with question;
2. follow-up message completes it → `awaiting_approval` + `quote_id`;
3. inbox lists it; detail shows extraction, items, totals, `pdf_url` that downloads;
4. `edit` → revision 2; `approve` → status `approved`;
5. second `approve` → 409;
6. message while pending → `busy`.

## Risks / open questions
- Long LLM latency on `/chat/send`: acceptable for MVP (a few seconds). If not, return 202 and let the client poll messages.

## Notes / changelog
- 2026-10-31: phase file created.
