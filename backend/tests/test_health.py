import httpx

from app import __version__
from app.config import Settings


async def test_health_ok(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}


async def test_lifespan_creates_storage_dir(client: httpx.AsyncClient, settings: Settings) -> None:
    assert settings.storage_dir.is_dir()
