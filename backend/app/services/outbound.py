"""How messages reach the customer. The MVP writes them to the in-app chat; a WhatsApp/SMS/email
channel can implement the same protocol later (Phase 13 stretch)."""

from typing import Protocol

from app.db.repo import Repo


class Outbound(Protocol):
    async def send(
        self, conversation_id: str, text: str, *, quote_id: str | None = None, kind: str = "text"
    ) -> None: ...


class InAppOutbound:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    async def send(
        self, conversation_id: str, text: str, *, quote_id: str | None = None, kind: str = "text"
    ) -> None:
        await self.repo.add_message(conversation_id, "business", text, quote_id=quote_id, kind=kind)
