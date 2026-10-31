# Phase 13: Hardening & demo

- **Status:** Done (Docker build untested locally)
- **Depends on:** [09](phase-09.md), [11](phase-11.md), [12](phase-12.md)
- **Decisions:** [D-011](../decisions.md#d-011), [D-012](../decisions.md#d-012), [D-013](../decisions.md#d-013)

## Goal
Anyone can clone the repo and see the full story working in minutes, and you can present it confidently.

## Scope
**In:** Docker/compose, seed data, CI, README polish, demo script, pitch notes, known limitations.
**Out:** production deployment, auth, multi-tenant.

## Deliverables
```
backend/Dockerfile                    # includes WeasyPrint system deps (D-012)
frontend/Dockerfile
docker-compose.yml                    # backend :8000, frontend :3000, volume for storage/
backend/scripts/seed_demo.py          # sample conversations in each state
.github/workflows/ci.yml              # ruff, pytest, evals replay, frontend lint+build
docs/demo-script.md
docs/pitch.md
README.md                             # quickstart, screenshots/GIF, eval numbers, architecture link
```

## Tasks
- [x] `docker compose up` → both apps running (written; not built locally since Docker is unavailable).
- [x] Health checks; `uvicorn --workers 1` documented ([D-013](../decisions.md#d-013)).
- [x] Error states in UI (backend down, LLM timeout) show friendly messages.
- [x] CI green.
- [x] Demo script (5 min): Hinglish voice note → clarify → complete → owner edits + discount → approve
      → customer gets PDF → fast-forwarded follow-up → injection attempt fails.
- [x] Pitch notes: "a workflow, not an agent" framing, the 3 strongest decisions (D-002, D-007, D-009),
      eval numbers, honest limits.
- [x] Known limitations section: single business, no auth, SQLite single writer, simulated channel,
      illustrative GST rates.

## Exit criteria
- Fresh clone on a clean machine → `docker compose up` → demo script runs without manual fixes.
- README shows eval numbers and an architecture diagram.

## Risks / open questions
- Stretch: real WhatsApp Business API channel via the Outbound protocol from Phase 11.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-13-hardening`.
  - `backend/Dockerfile` (python 3.12-slim, non-root, `/data` volume, healthcheck, `--workers 1`),
    `frontend/Dockerfile` (Next standalone, non-root), `docker-compose.yml` (demo mode by default,
    `backend/.env` optional). **Not built here:** Docker isn't installed on the dev machine.
  - `.github/workflows/ci.yml`: ruff, pytest, eval gate (`--min-total-match 1.0`), frontend lint +
    tsc + build. All steps run locally and pass.
  - `scripts/seed_demo.py`: seeds 6 conversations covering awaiting, sent, clarification, edited
    revision, accepted and refused (tested).
  - Catch-all 500 handler with the standard error envelope; internals are logged, never returned.
  - `.gitattributes` normalises line endings (fixes the CRLF warnings).
  - Docs: README rewritten (quickstart, Docker, real LLM, eval table, limits), `docs/demo-script.md`,
    `docs/pitch.md`, final graph diagram in `project.md` §3.2.
  - Tests: 418 offline.
