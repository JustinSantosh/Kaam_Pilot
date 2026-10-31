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


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(storage_dir=tmp_path / "storage", business_state="CG", _env_file=None)


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
        yield client
