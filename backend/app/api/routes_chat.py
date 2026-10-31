from fastapi import APIRouter, Query, Request

from app.api.views import message_out
from app.schemas.api import ChatSendRequest, ChatSendResponse, MessageOut

router = APIRouter(prefix="/api", tags=["customer"])


@router.post("/chat/send", response_model=ChatSendResponse)
async def send(body: ChatSendRequest, request: Request) -> ChatSendResponse:
    result = await request.app.state.runtime.handle_message(
        body.conversation_id, body.message, customer=body.customer.model_dump()
    )
    return ChatSendResponse(**result.model_dump())


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def messages(
    conversation_id: str, request: Request, since: int = Query(0, ge=0)
) -> list[MessageOut]:
    """Polled by the Customer Hub (D-016); `since` is the last message id the client has."""
    repo = request.app.state.repo
    rows = await repo.list_messages(conversation_id, since_id=since)
    quote_ids = {m.quote_id for m in rows if m.kind == "quote" and m.quote_id}
    pdfs = {}
    for qid in quote_ids:
        quote = await repo.get_quote(qid)
        pdfs[qid] = quote.pdf_path if quote else None
    return [message_out(m, pdfs) for m in rows]
