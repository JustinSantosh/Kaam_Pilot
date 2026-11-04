"""Stateless, signed owner sessions for the Business Ops API."""

import hashlib
import hmac
import time
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.config import Settings

COOKIE_NAME = "kaampilot_owner_session"
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


def _signature(password: str, expires_at: int) -> str:
    return hmac.new(password.encode(), str(expires_at).encode(), hashlib.sha256).hexdigest()


def _valid_session(token: str | None, settings: Settings) -> bool:
    password = settings.owner_password.get_secret_value()
    if not password or not token:
        return False
    try:
        raw_expiry, signature = token.split(".", 1)
        expires_at = int(raw_expiry)
    except (ValueError, TypeError):
        return False
    return expires_at > int(time.time()) and hmac.compare_digest(
        signature, _signature(password, expires_at)
    )


def require_owner(request: Request) -> None:
    if not _valid_session(request.cookies.get(COOKIE_NAME), request.app.state.settings):
        raise HTTPException(status_code=401, detail="owner login required")


@router.post("/login")
async def login(
    body: Annotated[LoginRequest, Body()], request: Request, response: Response
) -> dict[str, bool]:
    settings: Settings = request.app.state.settings
    expected = settings.owner_password.get_secret_value()
    if not expected:
        raise HTTPException(status_code=503, detail="owner authentication is not configured")
    if not hmac.compare_digest(body.password, expected):
        raise HTTPException(status_code=401, detail="invalid owner password")

    expires_at = int(time.time()) + settings.owner_session_ttl_seconds
    token = f"{expires_at}.{_signature(expected, expires_at)}"
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.owner_session_ttl_seconds,
        httponly=True,
        secure=settings.owner_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True}


@router.get("/session", dependencies=[Depends(require_owner)])
async def session() -> dict[str, bool]:
    return {"authenticated": True}


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": False}
