import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from langgraph.graph.state import CompiledStateGraph

from app.config import Settings
from app.db.repo import Repo
from app.main import create_app
from tests.fakes import FakeBrain

# Tests must not depend on the developer's shell or .env. Importing app.main has already cached
# get_settings(), which is all `pytest -m llm` needs from here.
for key in [k for k in os.environ if k.startswith("KP_")]:
    del os.environ[key]
os.environ["LANGSMITH_TRACING"] = "false"  # test runs never send traces, even if .env enables them


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        storage_dir=tmp_path / "storage",
        business_state="CG",
        owner_password="test-owner-password",
        _env_file=None,
    )


@pytest.fixture
def brain() -> FakeBrain:
    return FakeBrain()


@pytest.fixture
async def app(settings: Settings, brain: FakeBrain) -> AsyncIterator[FastAPI]:
    app = create_app(settings, deps_factory=brain.deps_factory)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
def graph(app: FastAPI) -> CompiledStateGraph:
    return app.state.graph


@pytest.fixture
def repo(app: FastAPI) -> Repo:
    return app.state.repo


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={"password": "test-owner-password"})
        assert response.status_code == 200
        yield client
