import re
import secrets
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile

from app.api.views import message_out
from app.llm import demo
from app.schemas.api import ChatSendRequest, ChatSendResponse, CustomerIn, MessageOut

router = APIRouter(prefix="/api", tags=["customer"])

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # ~2 minutes of compressed speech
AUDIO_TYPES = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}
_CONV_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@router.post("/chat/send", response_model=ChatSendResponse)
async def send(body: ChatSendRequest, request: Request) -> ChatSendResponse:
    result = await request.app.state.runtime.handle_message(
        body.conversation_id, body.message, customer=body.customer.model_dump()
    )
    return ChatSendResponse(**result.model_dump())


@router.post("/chat/send-audio", response_model=ChatSendResponse)
async def send_audio(
    request: Request,
    conversation_id: Annotated[str, Form()],
    audio: Annotated[UploadFile, File()],
    name: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    state: Annotated[str | None, Form()] = None,
) -> ChatSendResponse:
    """Voice note → transcript → the same path as typed text (guardrail, intent, extraction)."""
    if not _CONV_ID.match(conversation_id):
        raise HTTPException(422, "invalid conversation_id")
    mime = (audio.content_type or "").split(";")[0].strip()
    if mime not in AUDIO_TYPES:
        raise HTTPException(415, f"unsupported audio type {mime!r}")
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "voice note must be under 5 MB")
    transcribe = request.app.state.deps.transcribe
    if transcribe is None:
        raise HTTPException(503, "voice notes need a configured LLM")

    settings = request.app.state.settings
    target = settings.storage_dir / "audio" / conversation_id
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{secrets.token_hex(6)}.{AUDIO_TYPES[mime]}").write_bytes(data)

    text = (await transcribe(data, mime)).strip()
    if not text:
        raise HTTPException(422, "couldn't hear any speech in that voice note")
    customer = CustomerIn(name=name, phone=phone, state=state).model_dump()
    result = await request.app.state.runtime.handle_message(
        conversation_id, text, customer=customer, kind="voice"
    )
    return ChatSendResponse(**result.model_dump())


@router.get("/demo/scenarios")
async def demo_scenarios() -> list[dict[str, str | None]]:
    """Preset messages for the Customer Hub's scenario buttons."""
    return [
        {
            "id": sc["id"],
            "label": sc["label"],
            "message": sc["message"],
            "follow_up": (sc.get("follow_up") or {}).get("message"),
        }
        for sc in demo.scenarios()
    ]


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
