# Phase 04: Graph core & persistence

- **Status:** Not started
- **Depends on:** [02](phase-02.md), [03](phase-03.md)
- **Decisions:** [D-001](../decisions.md#d-001), [D-004](../decisions.md#d-004), [D-007](../decisions.md#d-007), [D-008](../decisions.md#d-008), [D-011](../decisions.md#d-011)

## Goal
The LangGraph workflow runs end to end up to (but not including) human approval, with durable
checkpoints and a quotes table as the system of record.

## Scope
**In:** `AgentState`, nodes `intent`, `extract`, `validate`, `clarify_draft`, `cancel_handler`,
`reply_draft`, `price`, a stub `render_pdf`; topology; `AsyncSqliteSaver`; SQLAlchemy models + repo.
**Out:** `interrupt()` / resume (Phase 05), real PDF (Phase 06), HTTP routes (Phase 07), guardrail
and transcribe nodes (Phase 10, added as pass-through stubs now).

## Deliverables
```
backend/app/agent/state.py
backend/app/agent/nodes/{intent,extract,validate,drafts,price,render_pdf}.py
backend/app/agent/graph.py          # build_graph(checkpointer) → compiled graph
backend/app/db/models.py            # conversations, quotes, quote_items, quote_events
backend/app/db/session.py           # async engine + sessionmaker
backend/app/db/repo.py              # create_quote, save_revision, set_status, add_event, list_by_status
backend/tests/test_graph_paths.py
backend/tests/test_repo.py
```

## Tasks
- [ ] `AgentState` per [project.md §5.2](../project.md#52-graph-state-agentstate).
- [ ] Nodes are thin: each calls a service function and returns a partial state update.
- [ ] Graph routes: `intent` → (`cancel_handler` | `reply_draft` | `extract`) → `validate` →
      (`clarify_draft` | `price`) → `render_pdf` → END (HITL is added in Phase 05).
- [ ] `price` creates/updates the quote row (`status=draft`, revision 1) via repo: idempotent upsert
      on `(quote_id, revision)`.
- [ ] Lifespan: open `AsyncSqliteSaver` (`storage/checkpoints.db`) and the async engine
      (`storage/kaampilot.db`); create tables (Alembic is optional; `create_all` is fine for MVP).
- [ ] Add `graph` to `app.state` for routes in Phase 07.
- [ ] Tests mock `classify_intent` / `extract` (monkeypatch at `llm/functions.py`).

## Exit criteria
- Graph tests cover: cancel path, other path, incomplete → clarify (message lists the exact missing
  fields), complete → priced quote row in DB with correct totals.
- Running the same thread twice after a restart (new saver instance on the same file) shows the persisted state.
- `list_by_status("draft")` returns the quote.

## Risks / open questions
- What `cancel` cancels: the latest open quote on the conversation (MVP). Record this in Phase 05 if it changes.
- Message history growth: keep `messages` but feed only `raw_query` + last N turns to the LLM.

## Notes / changelog
- 2026-10-31: phase file created.
