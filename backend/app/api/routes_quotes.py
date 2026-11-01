from typing import Annotated

from fastapi import APIRouter, Body, Query, Request

from app.api.views import detail
from app.db.repo import NotFoundError
from app.schemas.api import QuoteDetail
from app.schemas.decision import Decision

router = APIRouter(prefix="/api/quotes", tags=["business"])


async def _detail(request: Request, quote_id: str) -> QuoteDetail:
    repo = request.app.state.repo
    quote = await repo.get_quote(quote_id)
    if quote is None:
        raise NotFoundError(f"quote {quote_id}")
    waiting = await request.app.state.runtime.pending(quote.conversation_id)
    errors = waiting.get("edit_errors", []) if waiting and waiting["quote_id"] == quote_id else []
    return await detail(repo, quote, errors)


@router.get("/{quote_id}", response_model=QuoteDetail)
async def get_quote(quote_id: str, request: Request) -> QuoteDetail:
    return await _detail(request, quote_id)


@router.post("/{quote_id}/decision", response_model=QuoteDetail)
async def decide(
    quote_id: str,
    request: Request,
    decision: Annotated[Decision, Body()],
    revision: int | None = Query(None, ge=1, description="Revision the owner was looking at"),
) -> QuoteDetail:
    """Approve, reject (with reason) or edit (structured changes; never a raw total, D-009)."""
    if await request.app.state.repo.get_quote(quote_id) is None:
        raise NotFoundError(f"quote {quote_id}")
    await request.app.state.runtime.decide(quote_id, decision, revision=revision)
    return await _detail(request, quote_id)
