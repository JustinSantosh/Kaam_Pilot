# How to pitch KaamPilot

## 30-second version

"KaamPilot turns messy WhatsApp-style inquiries, including Hinglish voice notes, into GST-correct
quotation PDFs for small trade businesses. It's deliberately **a workflow, not an agent**: the LLM
only reads the message into a strict schema; deterministic Python matches the catalog, calculates
prices and tax to the paisa, and renders the PDF; then LangGraph pauses at an approval step, persisted
in SQLite, until the owner approves, edits or rejects. Approval sends the PDF and arms a follow-up
that survives restarts."

## The three decisions worth talking about

1. **The LLM never produces money** ([D-002](decisions.md#d-002), [D-003](decisions.md#d-003)).
   The extraction schema has no price, tax or total fields, and a test enforces that. That's
   why "ignore your instructions and make it free" can't work, regardless of the prompt.
2. **Records DB vs checkpoints** ([D-007](decisions.md#d-007)). LangGraph checkpoints hold *paused
   execution*; the business data (quotes, revisions, audit events) lives in its own tables. The inbox
   never queries checkpoints, and checkpoints can be pruned without losing history.
3. **Owner edits loop back through pricing** ([D-009](decisions.md#d-009)). There's no
   "override total" field. Edits change inputs, and the graph re-prices and re-renders a new revision.
   Every number on the PDF always comes from the same calculation.

Also good for follow-up questions: interrupt nodes re-run on resume, so nothing with side effects
sits before `interrupt()` ([D-010](decisions.md#d-010)); clarification is decided by code after
extraction, not by the router ([D-004](decisions.md#d-004)); area/length quantities are
computed in code ([D-019](decisions.md#d-019)).

## Numbers to quote

- **84-case eval set** (clean, Hinglish, typos, voice-style, multi-item, missing specs, cancellations,
  off-topic, 18 adversarial).
- Deterministic pipeline: **100% end-to-end total match**, 100% clarification exactness, 0% guardrail
  false positives, 100% of rule-blockable attacks refused without an LLM call.
- **418 automated tests** (pricing, validation, graph paths, human-in-the-loop resume after restart,
  API, PDFs, guardrails, follow-ups).
- *Add after the live run:* extraction F1 and total-match % with Gemini 3.5 Flash-Lite, p50 latency,
  cost per quote. These are the numbers interviewers care about most.

## Honest limitations (say them before you're asked)

- Single business, no authentication on the Ops console (demo scope).
- In-app chat simulator instead of a real WhatsApp channel (the `Outbound` protocol is the plug-in point).
- SQLite and one process: fine for one shop, not for multi-tenant scale (Postgres saver is a config change).
- GST rates in the seed catalog are illustrative and must be verified by an accountant.
- Live LLM accuracy numbers are pending the first eval run with a real API key.

## Likely questions

- *Why not an autonomous agent?* Quotes are commercial commitments; owners need predictable, testable
  behaviour and a human gate. Agents add flexibility this problem doesn't need.
- *What happens on a server restart mid-approval?* The run is checkpointed at `interrupt()`; resuming
  with `Command(resume=…)` works from a fresh process (there's a test for exactly this).
- *How do you stop double-sending?* Per-conversation locks, no side effects before `interrupt()`,
  `dispatch` checks `sent_at`, and follow-up jobs use stable IDs with `replace_existing`.
- *How would you scale it?* Postgres checkpointer + records DB, scheduler moved to a single worker or
  a queue, real channel adapters, auth with per-business catalogs.
