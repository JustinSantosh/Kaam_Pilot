from fastapi import APIRouter, Query, Request

from app.api.views import summary
from app.db.repo import OPEN_STATUSES, TERMINAL_STATUSES
from app.schemas.api import CatalogOption, QuoteSummary

router = APIRouter(prefix="/api/business", tags=["business"])

STATUS_FILTERS = {
    "awaiting_approval": ["awaiting_approval"],
    "open": list(OPEN_STATUSES),
    "closed": list(TERMINAL_STATUSES),
    "all": None,
}


@router.get("/inbox", response_model=list[QuoteSummary])
async def inbox(
    request: Request,
    status: str = Query("awaiting_approval", pattern="^(awaiting_approval|open|closed|all)$"),
) -> list[QuoteSummary]:
    repo = request.app.state.repo
    quotes = await repo.list_quotes(STATUS_FILTERS[status])
    convs = await repo.conversations(q.conversation_id for q in quotes)
    counts = await repo.item_counts([q.id for q in quotes])
    return [summary(q, convs.get(q.conversation_id), counts.get(q.id, 0)) for q in quotes]


@router.get("/catalog", response_model=list[CatalogOption])
async def catalog(request: Request) -> list[CatalogOption]:
    """For the owner's edit drawer: which SKUs exist and which spec options they allow."""
    return [
        CatalogOption(
            sku=i.sku,
            name=i.name,
            category=i.category,
            unit=i.unit,
            moq=i.moq,
            required_specs=i.required_specs,
            spec_options={k: sorted(v) for k, v in i.spec_surcharges.items()},
        )
        for i in request.app.state.catalog.items
    ]
