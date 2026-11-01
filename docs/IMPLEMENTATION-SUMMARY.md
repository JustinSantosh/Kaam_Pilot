# What was built, phase by phase

KaamPilot as of 2026-11-01: **13 phases built**, 418 offline tests passing, 84-case eval set,
24 recorded decisions, ~10.5k lines across backend, frontend and docs. Each phase's own file in
[`phases/`](phases/) has the full checklist and changelog; this page is the overview.

Status legend: ✅ done and verified · 🟡 done, one part waits on something only you can do
(see [YOUR-TODO.md](YOUR-TODO.md)).

| Phase | Branch | Status |
|---|---|---|
| 01 Foundations | `main` | ✅ |
| 02 Pricing | `main` | ✅ |
| 03 Extraction | `phase-03-extraction` | 🟡 live LLM check |
| 04 Graph core | `phase-04-graph` | ✅ |
| 05 Human-in-the-loop | `phase-05-hitl` | ✅ |
| 06 PDF | `phase-06-pdf` | ✅ |
| 07 API | `phase-07-api` | ✅ |
| 08 Customer Hub | `phase-08-customer-hub` | ✅ |
| 09 Business Ops | `phase-09-ops-console` | ✅ |
| 10 Guardrails & voice | `phase-10-guardrails-voice` | 🟡 live voice check |
| 11 Dispatch & follow-ups | `phase-11-dispatch` | ✅ |
| 12 Evals | `phase-12-evals` | 🟡 live eval run |
| 13 Hardening & demo | `phase-13-hardening` | 🟡 Docker build untested |

---

## Phase 01: Foundations & project docs
- FastAPI app factory with a lifespan hook, `/health`, CORS, typed settings from `KP_*` env vars.
- pytest + pytest-asyncio + httpx test client; ruff lint/format.
- The documentation set: `project.md`, `decisions.md`, 13 phase plans; CodeRabbit config and a
  PR-per-phase workflow.

## Phase 02: Catalog & deterministic pricing
- `catalog.json` (10 seed items across apparel, fabrication, carpentry, printing), validated on load:
  tiers ascend, GST slabs end open-ended, surcharge specs must be required, SKUs unique.
- `price_quote()`: tier price + option surcharges, MOQ, setup fee, owner discount split by
  largest remainder, GST slab on post-discount per-unit value, CGST+SGST vs IGST, per-line half-up rounding.
- Integer paise everywhere; Indian number formatting.
- **Tests:** tier/slab boundaries, rounding, discounts, 200 random carts checking that totals add up.
- **Decisions:** D-005, D-006, D-018.

## Phase 03: Schemas & LLM extraction 🟡
- LLM-facing schemas with **no money fields** (a test enforces it); provider-agnostic model loader.
- Intent and extraction prompts (Hinglish examples, spec vocabulary generated from the catalog,
  customer text fenced as data).
- Fuzzy SKU matcher (`matched / ambiguous / none`); validator for quantity, MOQ, required specs and
  options; **sqft/rft quantity computed in code from dimensions**; clarification questions built from
  the validation result.
- Gemini 3.5 Flash-Lite chosen as the default (D-020, *Proposed*); `.env` keys load into the environment.
- **Pending:** live golden test (`pytest -m llm`) and confirming the model.
- **Decisions:** D-003, D-004, D-014, D-019, D-020.

## Phase 04: Graph core & persistence
- LangGraph workflow: ingest → guardrail → intent → extract → validate → clarify | price → PDF, plus
  cancel and small-talk branches.
- Records DB (SQLAlchemy async on SQLite): conversations, messages, quotes, revisions, audit events.
- `AsyncSqliteSaver` checkpoints; clarification across several messages; Indian state/city → GST state code.
- **Tests:** every graph path, state surviving a new checkpointer instance.
- **Decisions:** D-007, D-011.

## Phase 05: Human-in-the-loop
- `interrupt()` approval step; approve / structured edit / reject via `Command(resume=…)`.
- Edits re-price into a **new revision** (history kept); invalid edits come back with errors.
- `Runtime`: per-conversation lock, new messages during review become notes ("busy"), stale-revision guard.
- **Tests:** approve after a simulated restart, exact event sequence (no duplicate side effects).
- **Decisions:** D-008, D-009, D-010.

## Phase 06: Quotation PDF
- Jinja2 template rendered by xhtml2pdf (WeasyPrint needs GTK on Windows): business header, quote
  number/revision/validity, HSN, specs, discount, CGST/SGST or IGST, amount in words, terms.
- Draft PDF for review, final PDF on approval; strict `/files/quotes/...` route.
- **Tests:** PDF text extracted and compared with stored totals; path traversal → 404.
- **Decisions:** D-021 (supersedes D-012).

## Phase 07: API layer
- `/api/chat/send`, `/api/conversations/{id}/messages?since=`, `/api/business/inbox`,
  `/api/business/catalog`, `/api/quotes/{id}`, `/api/quotes/{id}/decision?revision=`.
- One error envelope; 409s for stale or non-pending quotes; `docs/openapi.json`.
- **Tests:** the full HTTP flow end to end.

## Phase 08: Customer Hub (frontend)
- Next.js 16 + React 19.2 + Tailwind v4 (upgraded from 15.5 to clear security advisories; 0 npm audit findings).
- Demo customers, scenario presets served by the backend, polled chat, status chips, PDF cards.
- **Offline demo brain** (`KP_LLM_MODEL=demo`) so everything runs without a key.
- **Verified in the browser.** **Decisions:** D-022, D-023.

## Phase 09: Business Ops console
- Inbox with filters and pending badge; three-panel inspector (customer said / AI understood /
  priced by code); edit drawer (products, quantities, specs, discount; no total field); approve and
  reject dialogs; PDF viewer; history.
- **Verified in the browser:** an edit to 150 pcs with 5% discount re-priced to ₹30,423.76 (checked by hand).

## Phase 10: Guardrails & voice 🟡
- Injection rules refuse without an LLM call; money-override phrases flag the quote; LLM risk check
  that fails open; polite refusal path.
- Voice notes: `/api/chat/send-audio`, transcription before the graph, mic button.
- **Tests:** 18 adversarial cases plus a false-positive check on the golden set.
- **Pending:** real Gemini audio transcription. **Decisions:** D-015, D-024.

## Phase 11: Dispatch & follow-ups
- Approval sends the final PDF as a chat message; status → sent.
- 48-hour follow-up on a persistent APScheduler job store: sent at most once, cancelled on any reply or
  cancel; a bare "YES" accepts the quote.
- **Tests:** jobs survive a restart, a real timer fires. **Verified in the browser.** **Decision:** D-013.

## Phase 12: Evals & observability 🟡
- 84 labelled cases (clean, Hinglish, typos, voice-style, multi-item, missing, cancel, off-topic, adversarial).
- Runner with `ideal` (CI gate), `live` and `replay` modes; per-field metrics, clarification exactness,
  end-to-end total match, guardrail block / false-positive rates, latency, per-category table.
- Ideal-mode results: **100% total match**, 100% clarification exactness, 0% false positives.
- LangSmith run names, prompt-version tags, conversation metadata.
- **Pending:** live run, model comparison, error analysis. **Decision:** D-017.

## Phase 13: Hardening & demo 🟡
- Dockerfiles (non-root, healthcheck, one worker) and `docker-compose.yml` (demo mode by default).
- GitHub Actions CI: lint, tests, eval gate, frontend lint/types/build (all pass locally).
- Seed script for every quote state; catch-all 500 envelope; line-ending normalisation.
- README, [demo script](demo-script.md), [pitch notes](pitch.md).
- **Pending:** first Docker build (Docker isn't installed on the dev machine).
