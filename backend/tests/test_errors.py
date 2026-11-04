import httpx
import pytest
from fastapi import FastAPI


async def test_unexpected_errors_use_the_envelope_without_leaking(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(app.state.runtime, "handle_message", boom)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post("/api/chat/send", json={"conversation_id": "c", "message": "hi"})
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "internal_error"
    assert "secret" not in resp.text


async def test_chat_rate_limit_uses_error_envelope(client: httpx.AsyncClient, settings) -> None:
    settings.chat_rate_limit_per_minute = 1
    body = {"conversation_id": "c_rate", "message": "hello"}
    first = await client.post("/api/chat/send", json=body)
    limited = await client.post("/api/chat/send", json=body)

    assert first.status_code == 200
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert limited.headers["retry-after"]
