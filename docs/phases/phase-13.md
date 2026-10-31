# Phase 13: Hardening & demo

- **Status:** Not started
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
- [ ] `docker compose up` → both apps running, seeded inbox.
- [ ] Health checks; `uvicorn --workers 1` documented ([D-013](../decisions.md#d-013)).
- [ ] Error states in UI (backend down, LLM timeout) show friendly messages.
- [ ] CI green.
- [ ] Demo script (5 min): Hinglish voice note → clarify → complete → owner edits + discount → approve
      → customer gets PDF → fast-forwarded follow-up → injection attempt fails.
- [ ] Pitch notes: "a workflow, not an agent" framing, the 3 strongest decisions (D-002, D-007, D-009),
      eval numbers, honest limits.
- [ ] Known limitations section: single business, no auth, SQLite single writer, simulated channel,
      illustrative GST rates.

## Exit criteria
- Fresh clone on a clean machine → `docker compose up` → demo script runs without manual fixes.
- README shows eval numbers and an architecture diagram.

## Risks / open questions
- Stretch: real WhatsApp Business API channel via the Outbound protocol from Phase 11.

## Notes / changelog
- 2026-10-31: phase file created.
