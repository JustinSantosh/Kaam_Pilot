# What was built, phase by phase

KaamPilot as of 2026-11-11: **13 phases built** plus the audit and hardening pass (GitHub PR #13),
an offline test suite that needs no API key (`pytest -q` prints the current count), an 84-case eval
set and 26 recorded decisions. Each phase's own file in [`phases/`](phases/) has the full checklist
and changelog; this page is the overview. [`AUDIT.md`](AUDIT.md) records what the audit found and
what is still open.

Status legend: ✅ done and verified · 🟡 done, one part waits on something only you can do
(see [YOUR-TODO.md](YOUR-TODO.md)). Every branch below is merged into `main`; the Branch column
records where each phase was built.

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
| Audit & hardening (PR #13) | `feat/audit-hardening` | 🟡 live provider failures unchecked; open items in [AUDIT.md](AUDIT.md) |

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
- Gemini 3.5 Flash-Lite chosen as the default (D-020, *Proposed*); provider keys in `.env` (such as
  `GOOGLE_API_KEY`) load into the environment.
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
- Next.js 16 + React 19.2 + Tailwind v4 (upgraded from 15.5 to clear security advisories; `npm audit`
  reported 0 findings at the time).
- **`npm audit` on 2026-11-11:** 8 moderate findings, all from one `minimatch` advisory
  (GHSA-g3hv-75wg-m249) that reaches the ESLint toolchain. AUD-16 in [AUDIT.md](AUDIT.md) recorded 16
  on 2026-11-04 for the same lockfile. `npm audit --omit=dev` reports 0, so none are in the runtime
  dependencies.
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

## Audit & hardening (GitHub PR #13) 🟡
Not a numbered phase: a repository audit ([AUDIT.md](AUDIT.md), 2026-11-04) and the fixes made from it.
- **Owner sign-in** ([D-025](decisions.md#d-025)): `POST /api/auth/login` checks `KP_OWNER_PASSWORD` and sets a
  signed, HttpOnly session cookie. The inbox, catalog, quote detail and decisions, and draft PDFs need it;
  final PDFs stay open to the customer after approval. Business Ops shows an "Owner sign in" form.
- **LLM calls:** one overall timeout (`KP_LLM_TIMEOUT_SECONDS`, default 30) and up to 3 attempts with
  backoff for transient failures. A failure returns `503 llm_unavailable` instead of a generic 500.
- **Chat rate limit** ([D-026](decisions.md#d-026)): `POST /api/chat/send` and `/api/chat/send-audio` are limited per
  client IP (default 30 a minute, `KP_CHAT_RATE_LIMIT_PER_MINUTE`); over the limit gives `429 rate_limited`.
  The counter is in memory, so it only works with one process.
- **`GET /ready`:** checks the records DB, the checkpointer and the scheduler (200, or 503 if one is down).
  The records DB also gets a SQLite busy timeout, and startup warns if `WEB_CONCURRENCY` or
  `UVICORN_WORKERS` asks for more than one worker.
- **Serialized work:** customer messages, owner decisions and follow-up sends take the same
  per-conversation lock. Dispatch saves the sent status, final PDF path, audit events and chat message in
  one transaction, and a repeated dispatch does nothing.
- **Frontend:** polling runs one request at a time, pauses while the tab is hidden and backs off on errors;
  load errors are shown; the voice recorder has a Cancel button; `/` is now a landing page where you
  choose Customer Hub or Business Ops.
- **Config:** `.env.example` files for backend and frontend. With `KP_ENVIRONMENT=production` the backend
  refuses to start with a short owner password, wildcard CORS or non-Secure cookies.
- **Still open:** see [AUDIT.md](AUDIT.md) (for example multi-process safety, migrations, a Unicode PDF
  font, browser tests, dependency advisories). Live provider failure modes and the Docker build still
  need checking.
