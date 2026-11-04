import httpx
import pytest
from fastapi import FastAPI

from app.config import Settings
from app.schemas.decision import Approve


async def test_business_routes_require_owner_session(app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/api/business/inbox", "/api/business/catalog"):
            response = await client.get(path)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "unauthorized"
        draft = await client.get("/files/quotes/q_000000000000/r1-draft.pdf")
        assert draft.status_code == 401


async def test_login_sets_http_only_session_and_protects_quote_pdf(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    login = await client.post("/api/auth/login", json={"password": "test-owner-password"})
    assert "httponly" in login.headers.get("set-cookie", "").lower()
    response = await client.get("/api/auth/session")
    assert response.status_code == 200
    assert client.cookies.get("kaampilot_owner_session")
    result = await app.state.runtime.handle_message(
        "c_public_pdf",
        "50 hoodies chahiye black, back pe DTF print, sizes M 20 L 20 XL 10",
        customer={"name": "Ravi", "state": "CG"},
    )
    await app.state.runtime.decide(result.quote_id, Approve(action="approve"))
    client.cookies.clear()
    pdf = await client.get(f"/files/quotes/{result.quote_id}/r1.pdf")
    assert pdf.status_code == 200


async def test_bad_password_is_rejected(client: httpx.AsyncClient) -> None:
    client.cookies.clear()
    response = await client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "invalid owner password"


async def test_production_settings_require_secure_owner_configuration() -> None:
    with pytest.raises(ValueError, match="at least 16 characters"):
        Settings(
            environment="production",
            owner_password="short",
            owner_cookie_secure=True,
            _env_file=None,
        )
