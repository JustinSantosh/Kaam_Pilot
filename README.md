# KaamPilot

A human-in-the-loop quotation workflow for custom service and trade businesses (apparel printing,
fabrication, carpentry, interior contracting). It reads messy text, Hinglish or voice inquiries,
prices them with deterministic code, drafts a GST-correct PDF quote, and waits for the owner's
approval before anything reaches the customer.

**The LLM reads. Code calculates. The owner approves.**

```
Customer Hub ──► FastAPI ──► LangGraph workflow ──────────────────────────────► Business Ops
 (chat/voice)                guardrail → intent → extract (LLM, schema only)     inbox · inspector
                             → validate → price → PDF (pure Python)              edit · approve
                             → interrupt() ⏸ checkpointed in SQLite  ◄─────────── reject
                             → dispatch PDF → 48h follow-up (APScheduler)
```

## Quickstart (local, no API key needed)

Demo mode (`KP_LLM_MODEL=demo`) swaps the LLM for an offline stand-in that understands the preset
scenarios ([D-022](docs/decisions.md#d-022)). Everything else is the real code path.

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,google]"
KP_LLM_MODEL=demo uvicorn app.main:app --port 8000 --workers 1
```

```bash
# frontend (second terminal)
cd frontend
npm install
npm run dev                       # http://localhost:3000
```

Open **http://localhost:3000/customer**, click a scenario, then review it at **/business**.
Optional: seed a demo database with every state: `python -m scripts.seed_demo`.

### With Docker

```bash
docker compose up --build         # frontend :3000, backend :8000, demo mode by default
```

### With the real LLM (Gemini)

Put this in `backend/.env` (gitignored):

```
KP_LLM_MODEL=google_genai:gemini-3.5-flash-lite
GOOGLE_API_KEY=...
```

Then run the live checks: `pytest -m llm` (golden inquiries) and
`python -m evals.run_evals --mode live --record`.

## What's inside

| Area | Highlights |
|---|---|
| Pricing | Tiers, MOQ, spec surcharges, setup fees, owner discounts (largest-remainder split), GST slabs by HSN, CGST+SGST vs IGST by place of supply. Integer paise end to end. |
| Extraction | Strict Pydantic schemas with **no money fields**; catalog-driven spec vocabulary; Hinglish prompts; fuzzy SKU matcher; completeness decided in code; sqft/rft computed from dimensions in code. |
| Workflow | LangGraph with `interrupt()` / `Command(resume=…)`, `AsyncSqliteSaver` checkpoints, approve / structured edit (re-price into a new revision) / reject, safe resume after restart. |
| Records | SQLite (SQLAlchemy async): conversations, messages, quotes, revisions, audit events. The system of record, separate from checkpoints. |
| Documents | Jinja2 + xhtml2pdf quotation PDFs: draft for review, final on approval, amount in words. |
| Guardrails | Injection rules (no LLM call needed), money-override flags, LLM risk check that fails open. |
| Voice | Voice notes transcribed by the configured model, then the same pipeline as text. |
| Follow-ups | Persistent 48h follow-up jobs, sent at most once, cancelled on reply; "YES" confirms the order. |
| Frontend | Next.js 16 + Tailwind: Customer Hub (demo customers, presets, chat, mic) and Business Ops (inbox, three-panel inspector, edit drawer, PDF viewer). |
| Quality | 418 tests, 84-case eval set, CI (ruff, pytest, eval gate, frontend lint + build), CodeRabbit config. |

## Eval results

Deterministic pipeline (`python -m evals.run_evals --mode ideal`; CI gate):

| Metric | Value |
|---|---|
| End-to-end total match | **100%** |
| Clarification exactness | 100% |
| Item F1 / quantity / spec accuracy | 100% / 100% / 100% |
| Guardrail: rule-blockable attacks refused | 100% (no LLM call) |
| Guardrail false-positive rate | 0% |

Live LLM numbers (Gemini 3.5 Flash-Lite) will be added after the first `--mode live` run.

## Docs

- [Project spec](docs/project.md): architecture, data model, API, phase index, dev workflow
- [Decision log](docs/decisions.md): 24 decisions with why/why-not
- [Phases](docs/phases/): `phase-01.md` … `phase-13.md`, each with a changelog of what was built
- [Implementation summary](docs/IMPLEMENTATION-SUMMARY.md) · [Owner to-do](docs/YOUR-TODO.md)
- [Demo script](docs/demo-script.md) · [Pitch notes](docs/pitch.md) · [OpenAPI](docs/openapi.json)

## Known limitations

Single business and no auth on the Ops console · in-app chat instead of a real WhatsApp channel ·
SQLite + one process (`--workers 1`) · seed GST rates are illustrative · PDFs print "Rs." (no ₹
glyph in the built-in fonts) · live LLM accuracy not yet measured.
