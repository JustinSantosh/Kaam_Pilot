"""Serve generated quotation PDFs. Only names we generate are accepted, so no path from the
request ever reaches the filesystem unchecked."""

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()

_QUOTE_ID = re.compile(r"^q_[0-9a-f]{12}$")
_FILENAME = re.compile(r"^r\d{1,4}(-draft)?\.pdf$")


@router.get("/files/quotes/{quote_id}/{filename}", include_in_schema=False)
async def quote_pdf(quote_id: str, filename: str, request: Request) -> FileResponse:
    if not (_QUOTE_ID.match(quote_id) and _FILENAME.match(filename)):
        raise HTTPException(status_code=404)
    path = request.app.state.settings.storage_dir / "quotes" / quote_id / filename
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=f"{quote_id}-{filename}")
