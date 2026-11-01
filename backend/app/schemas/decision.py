"""The owner's decision on a quote awaiting approval (D-009). Edits are structured; there is no
way to type a total."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from app.schemas.pricing import Discount


class ItemEdit(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    specs: dict[str, str] | None = None  # None keeps the line's current specs


class Edits(BaseModel):
    items: list[ItemEdit] | None = Field(
        default=None, description="Full replacement list of lines; omit to keep the lines"
    )
    discount: Discount | None = None
    remove_discount: bool = False


class Approve(BaseModel):
    action: Literal["approve"]


class Reject(BaseModel):
    action: Literal["reject"]
    reason: str = Field(min_length=1, max_length=500)


class Edit(BaseModel):
    action: Literal["edit"]
    edits: Edits


Decision = Annotated[Approve | Reject | Edit, Field(discriminator="action")]
DecisionAdapter: TypeAdapter[Approve | Reject | Edit] = TypeAdapter(Decision)
