# KaamPilot repository audit

**Audit date:** 2026-11-04
**Branch:** `audit-and-hardening`
**Scope:** Backend/API, graph and persistence, pricing/PDF, frontend, CI/dependencies, docs, and
local browser flows. This is the baseline audit, recorded before remediation.

## Remediation progress

The audit findings below remain the baseline inventory. Work completed so far:

| IDs | Progress |
|---|---|
| AUD-01 | Added owner-password sign-in, signed HttpOnly sessions, protected business/quote routes, and draft-PDF authorization. Final dispatched PDFs remain customer-accessible. |
| AUD-02 | Dispatch persistence is transactional and decisions are serialized within one process; multi-worker startup warns. Database-level compare-and-set across processes and fully recoverable scheduling remain open. |
| AUD-03 | Added provider-call timeouts and bounded transient retries. Live provider failure modes still need credentials-backed validation. |
| AUD-04 | Added in-process chat rate limiting and standard error-envelope coverage. Limits remain process-local by design. |
| AUD-05 | Added SQLite busy timeout/pragmas, `/ready`, and a multi-worker warning. |
| AUD-06 | Serialized customer turns and follow-up work by conversation, made dispatch/follow-up effects idempotent, and added concurrency regression coverage. |
| AUD-07 | Reconciled the project topology with D-008's pending-review busy-note behavior. |
| AUD-10, AUD-11 | Replaced interval polling with sequential, visibility-aware polling and error backoff; surfaced scenario errors and added voice-recording cancellation. |
| AUD-12 | Replaced the redirecting home page with a role-selection landing page. The broader Ops/Customer redesign, dark theme, and accessibility review remain open. |
| AUD-18 | Added backend/frontend environment examples and production configuration checks. |

Still open: distributed decision concurrency, migrations/schema versioning, structured correlation
logging, durable follow-up recovery, bundled Unicode PDF font, broad UI redesign and E2E coverage,
dependency advisories, and Docker validation.

## Critical

None found in the baseline checks. Pricing remains deterministic and expressed in integer paise;
the extraction schema has no money fields; quote dispatch is behind the approval interrupt.

## High

| ID | File and lines | Symptom | Root cause | Planned fix |
|---|---|---|---|---|
| AUD-01 | `backend/app/main.py:76-80`; `backend/app/api/routes_business.py:18-38`; `backend/app/api/routes_quotes.py:29-39`; `backend/app/api/routes_files.py:16-23` | Inbox, catalog, quote detail/decisions, and generated PDFs are accessible without owner authentication. | Business and file routers have no authentication dependency or session boundary. | Add a configurable owner credential and secure session/API dependency for all business routes and PDFs; document setup and protect the Ops UI. |
| AUD-02 | `backend/app/agent/runtime.py:64-70,131-147`; `backend/app/db/repo.py:147-225`; `backend/app/agent/nodes.py:279-300` | Decision serialization is process-local; status/event updates, dispatch, scheduling, and the customer message are separate transactions. A worker restart between them can leave partial state; multiple workers can race. | `asyncio.Lock` is local to one `Runtime`, status writes have no compare-and-set, and dispatch side effects are not recorded atomically with the decision. | Make decisions conditional/atomic in the records DB, make dispatch and follow-up scheduling recoverable/idempotent, add restart/concurrency tests, and reject or warn on unsupported multi-worker operation. |
| AUD-03 | `backend/app/llm/provider.py:13-38`; `backend/app/agent/nodes.py:74-82`; `backend/app/api/errors.py:50-53` | LLM calls have no application timeout. Retries cover parse/validation errors only; provider timeout, rate limit, and malformed-output failures can become a generic 500 instead of a recoverable owner/clarification path. | The provider wrapper applies `with_retry` to two exception types but does not configure a timeout or translate provider errors. | Add bounded timeouts and backoff for transient provider failures, explicit error mapping, and safe fallback behavior; test timeout, rate limit, and malformed output. |
| AUD-04 | `backend/app/api/routes_chat.py:26-31,34-75` | Public chat and audio endpoints have no request-rate limit, allowing repeated model work and uploads. | No rate-limiting middleware/dependency is configured. | Add configurable per-client limits for chat and audio and return the standard 429 error envelope; cover it with tests. |

## Medium

| ID | File and lines | Symptom | Root cause | Planned fix |
|---|---|---|---|---|
| AUD-05 | `backend/app/db/session.py:16-28`; `backend/app/main.py:27-62,81-83` | SQLite enables WAL and foreign keys but not `busy_timeout`; `/health` is liveness-only and there is no readiness signal for DB, checkpointer, or scheduler. The app does not guard against multiple workers despite scheduler/lock assumptions. | SQLite connection setup is minimal and startup records no component readiness or process-count warning. | Configure SQLite busy timeout consistently, expose `/ready`, and clearly warn/fail when running an unsupported worker count. |
| AUD-06 | `backend/app/services/followups.py:82-112`; `backend/app/agent/runtime.py:99-112` | A follow-up can pass its status/reply checks while a customer response or acceptance is in progress, then send after the reply or update status twice. | Follow-up check, outbound message, and status change are separate operations and do not share the conversation lock or an atomic claim. | Serialize follow-up/reply work by conversation and atomically claim/send at most once; add race tests. |
| AUD-07 | `backend/app/agent/runtime.py:92-105`; `docs/project.md:119-133`; `docs/decisions.md:194-210` | The project graph says a customer can cancel a pending quote, but Runtime treats every message while an interrupt is pending as a `busy` note before it can classify cancellation. | The project topology and D-008 runtime contract disagree about cancellation during owner review. | Reconcile the docs and behavior explicitly. Preserve D-008's note semantics unless a separately recorded decision adds customer cancellation while pending. |
| AUD-08 | `backend/app/config.py:10-28`; `backend/app/main.py:48-62,76-83`; `backend/app/api/errors.py:50-53` | There is no request correlation ID or structured JSON logging, and no consistent readiness/trace status. Operational failures are difficult to tie to a conversation without inspecting user data. | Logging is a plain module logger and request metadata is only attached to LangGraph runs. | Add request-scoped correlation IDs and structured, PII-safe logs; expose readiness for the dependencies. |
| AUD-09 | `backend/app/api/routes_chat.py:34-75`; `.gitignore:9-14` | Audio is written to persistent storage and never removed; the 5 MB cap limits one upload but not cumulative storage or retention of voice/PII. File writing is synchronous inside the async route. | Upload lifecycle has no retention policy and writes use `Path.write_bytes` directly. | Make disk writes non-blocking, define bounded retention/cleanup, and add tests for size/type/cleanup. Keep `.env` excluded from Git. |
| AUD-10 | `frontend/src/hooks/usePolling.ts:6-26`; `frontend/src/app/customer/page.tsx:47-69`; `frontend/src/app/business/page.tsx:29-55` | Polling uses a fixed interval, can overlap slow requests, and discards thrown errors. Customer polling therefore can silently stop updating; quote-detail/catalog errors are not reliably surfaced. | The shared hook catches all errors without notifying its caller and schedules `setInterval` regardless of request duration. | Use sequential polling with backoff and visibility pause; expose errors to an alert/toast and retain/retry stale data safely. |
| AUD-11 | `frontend/src/app/customer/page.tsx:42-45`; `frontend/src/app/business/page.tsx:29-30`; `frontend/src/components/VoiceRecorder.tsx:28-65` | Scenario/catalog load failures silently become empty states. Voice recording has no cancel action or clear recording/send failure handling; stopping always submits the clip. | Several rejected promises are converted to empty data and the recorder only implements start/stop. | Show actionable errors, add cancel/discard and upload state, improve permission/type handling and accessible recording controls. |
| AUD-12 | `frontend/src/app/page.tsx:1-5`; `frontend/src/app/globals.css:1-16`; `frontend/src/components/Modal.tsx:5-43`; `frontend/src/app/business/page.tsx:17-98` | The requested polished product experience is incomplete: `/` redirects to Customer Hub; no dark theme or full component system; inbox lacks search/sort/status counts; loading/error states are inconsistent; dialogs do not trap/restore focus. | The current app is a small demo UI with hand-built primitives and only the initial chat/inbox workflows. | Redesign the landing and both role screens with accessible responsive tokens/components, complete inbox/inspector states, focus management, and visible feedback without changing the pricing/approval architecture. |
| AUD-13 | `backend/app/services/pdf.py:22-25`; `backend/app/services/money.py:19-22`; `backend/app/templates/quotation.html` | The PDF prints `Rs.` instead of the real rupee sign. | xhtml2pdf's built-in font lacks the glyph and no Unicode font is bundled. | Bundle/register a Unicode font and test PDF text/layout including Indian amount-in-words and long quotes. |
| AUD-14 | `backend/app/db/session.py:31-34`; `backend/app/db/models.py:44-110` | Startup uses `create_all`; there is no schema version or migration history. `updated_at` is not indexed for inbox/status queries. | Schema evolution is unmanaged and indexes cover only selected foreign keys/status columns. | Add migrations or a documented versioned schema strategy and appropriate query indexes with migration tests. |
| AUD-15 | `backend/tests/test_pricing.py`; `.github/workflows/ci.yml:22-50`; `frontend/package.json` | No property-based money invariants or browser end-to-end tests are present; CI has no dependency security scan. | Tests are example/matrix based and CI ends at lint, unit/eval checks, and frontend build. | Add property-based tests for line/quote/tax conservation, Playwright demo flows, and dependency auditing in CI. |
| AUD-16 | `frontend/package-lock.json` | `npm audit` reports 16 moderate transitive advisories involving `minimatch` in the ESLint toolchain; npm also warns that the resolved ESLint 9.39.5 version is deprecated. | Locked lint-tool dependencies resolve to vulnerable/out-of-support versions. | Update compatible transitive/tool versions, regenerate the lockfile without a breaking forced downgrade, and rerun lint/build/audit. |
| AUD-17 | `docs/project.md:145`; `docs/phases/phase-13.md:16`; `README.md:73`; `docs/IMPLEMENTATION-SUMMARY.md:3`; `docs/YOUR-TODO.md:34` | Docs still identify WeasyPrint/D-012 and claim 418 offline tests, while the implementation uses xhtml2pdf/D-021 and the baseline run collected 429, passed 419, and deselected 10 live tests. | Implementation and later decisions were not propagated to the project specification and metrics docs. | Reconcile the PDF stack references and update test/eval figures and limitations from verified commands. |
| AUD-18 | `backend/app/config.py:10-28`; repository root and `backend/`/`frontend/` | There are no backend/frontend `.env.example` files; config has no production checks for wildcard CORS or invalid operational settings. | Settings are spread across defaults without a validated deployment profile or complete sample env files. | Document every setting in example files; validate production CORS and credential configuration at startup. |

## Low

| ID | File and lines | Symptom | Root cause | Planned fix |
|---|---|---|---|---|
| AUD-19 | `README.md:73`; `docs/IMPLEMENTATION-SUMMARY.md:3`; `docs/YOUR-TODO.md:34` | The advertised offline test count is stale. Baseline: `pytest` collected 429, passed 419, deselected 10 (live LLM). | Test additions were not reflected in the documentation. | Update all maintained test counts after remediation and avoid hard-coding counts where practical. |
| AUD-20 | `backend/app/main.py:81-83`; `backend/app/api/errors.py:50-53` | Unhandled application exceptions are safely returned in the standard envelope, but all provider/PDF/scheduler failures collapse into a generic `internal_error`; some configured errors have no stable public code or recovery hint. | Only validation, not-found, conflict, and missing-LLM exceptions receive explicit mappings. | Add stable mappings and safe operational details for expected provider, PDF, scheduler, and database failures; do not expose stack traces or secrets. |

## Baseline verification

| Check | Result |
|---|---|
| `ruff check` | Passed. |
| `pytest` | **419 passed**, 10 live-LLM tests deselected; 13 dependency deprecation warnings from LangSmith (`asyncio.iscoroutinefunction`). |
| `python -m evals.run_evals --mode ideal` | 84 cases, 0 errors; total match 100%, outcome accuracy 97.6%, rule-blockable guardrail refusal 100%, overall adversarial block rate 81.8%, false-positive rate 0%. Two expected-refusal LLM-only adversarial cases were classified as `other`. |
| `npm run lint` | Passed after `npm ci`; initial attempt was blocked because `node_modules` was absent. |
| `npm run build` | Passed; Next.js 16.4.3 generated `/`, `/customer`, `/business`. |
| `npx tsc --noEmit` | Passed. |
| `npm audit` | Failed: 16 moderate transitive advisories in the ESLint/minimatch tree; no `npm audit fix` was applied during baseline audit. |
| Browser | Local demo exercised chat, clarification, edit/reprice, approval, PDF link, acceptance (`YES`), busy note, rejection, and injection refusal. Backend and frontend responded on localhost. A test page at `127.0.0.1:3000` hit the expected CORS rejection because configured origin is `localhost:3000`; switching to localhost worked. Audio permission/recording and actual 48-hour job firing were not verified. |
| Docker | Not run: Docker CLI is not installed in this environment. |
| Live Gemini | Not run: no provider credentials were supplied. The documented `gemini-3.5-flash-lite` model identifier is listed as Stable in the current official Gemini model documentation. |

The deterministic eval's 100% total-match result does not mean every adversarial expected outcome
passes: the two LLM-only refusal cases require the configured live risk classifier, while the ideal
mode uses the offline demo implementation.
