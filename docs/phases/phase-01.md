# Phase 01: Foundations & project docs

- **Status:** Done (pending first commit)
- **Depends on:** —
- **Decisions:** [D-001](../decisions.md#d-001), [D-011](../decisions.md#d-011), [D-014](../decisions.md#d-014)

## Goal
A clean, runnable skeleton that every later phase builds on: backend package, config, test and lint
tooling, a health endpoint, and the project docs.

## Scope
**In:** repo layout, `pyproject.toml`, FastAPI app with lifespan, settings, `/health`, pytest + ruff,
`.gitignore`, `.env.example`, docs (`project.md`, `decisions.md`, phase files).
**Out:** any business logic, LLM calls, frontend (Phase 08).

## Deliverables
```
README.md
docs/project.md, docs/decisions.md, docs/phases/*.md
backend/pyproject.toml
backend/.env.example
backend/app/__init__.py
backend/app/main.py            # create_app(), lifespan stub, /health
backend/app/config.py          # Settings(BaseSettings) with KP_* vars
backend/storage/.gitkeep
backend/tests/conftest.py      # app + async client fixtures
backend/tests/test_health.py
.gitignore                     # .venv, storage/*.db, storage/quotes/, .env, node_modules
```

## Tasks
- [x] `git init`, `.gitignore`. First commit still to do.
- [x] `pyproject.toml`: python ≥3.11; deps `fastapi`, `uvicorn[standard]`, `pydantic>=2`,
      `pydantic-settings`; dev deps `pytest`, `pytest-asyncio`, `httpx`, `ruff`.
- [x] `config.py`: `Settings` with `llm_model`, `business_state`, `storage_dir`, `followup_hours`,
      `cors_origins`; `get_settings()` cached.
- [x] `main.py`: `create_app()` factory, `lifespan` that creates `storage_dir` (DB/checkpointer/scheduler
      hooks added in later phases), CORS from settings, `GET /health → {"status": "ok", "version": …}`.
- [x] `conftest.py`: settings override pointing `storage_dir` at `tmp_path`; `httpx.AsyncClient` with `ASGITransport`.
- [x] Ruff config (line length, import sorting); `ruff check` clean.
- [x] README run instructions verified on Windows.

## Exit criteria
- `pytest` passes (`test_health` green).
- `uvicorn app.main:app` starts; `GET /health` returns 200.
- `ruff check .` is clean.
- Docs committed; every `D-xxx` link in docs resolves.

## Risks / open questions
- Package manager: `pip` + venv was used (no decision entry needed). `uv` also works with the same `pyproject.toml`.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-10-31: implemented. Python 3.12.6, FastAPI 0.162, pytest 9.2, ruff 0.17. `pytest`: 2 passed;
  `ruff check` and `ruff format --check` clean; `uvicorn app.main:app` serves `/health` 200 and `/openapi.json` 200.
  Live-LLM tests are excluded by default (`addopts = -m 'not llm'`); run them with `pytest -m llm`.
