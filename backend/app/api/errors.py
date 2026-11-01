"""One error shape for every failure: {"error": {"code", "message", "details"}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agent.runtime import QuoteNotPendingError, StaleRevisionError
from app.db.repo import NotFoundError
from app.llm.provider import LLMNotConfiguredError

logger = logging.getLogger("kaampilot")


def error(status: int, code: str, message: str, details: object = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(status_code=status, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return error(404, "not_found", f"{exc.args[0] if exc.args else 'resource'} not found")

    @app.exception_handler(QuoteNotPendingError)
    async def not_pending(_: Request, exc: QuoteNotPendingError) -> JSONResponse:
        return error(409, "quote_not_pending", "this quote is not waiting for a decision")

    @app.exception_handler(StaleRevisionError)
    async def stale(_: Request, exc: StaleRevisionError) -> JSONResponse:
        return error(409, "stale_revision", str(exc))

    @app.exception_handler(LLMNotConfiguredError)
    async def no_llm(_: Request, exc: LLMNotConfiguredError) -> JSONResponse:
        return error(503, "llm_not_configured", str(exc))

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()]
        return error(422, "validation_error", "request is invalid", details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Log server-side; never leak internals (stack traces, keys) to the client.
        logger.exception("unhandled error", exc_info=exc)
        return error(500, "internal_error", "something went wrong; please try again")
