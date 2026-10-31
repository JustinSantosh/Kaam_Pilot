"""What the LLM is allowed to produce (D-003).

These models are handed to `with_structured_output`, so they must never contain a price, rate, tax,
discount or total field (D-002). Specs are a list of name/value pairs rather than a dict because
providers' strict JSON-schema modes reject free-form object keys.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Spec(BaseModel):
    name: str = Field(description="Spec name from the vocabulary, e.g. 'print_type'")
    value: str = Field(description="Spec value in English, e.g. 'embroidery' or 'M:10, L:15'")


class ExtractedItem(BaseModel):
    item_text: str = Field(
        description="Short English description of the product asked for, e.g. 'black round-neck "
        "t-shirt'. Keep colour and type words; drop quantities."
    )
    quantity: int | None = Field(
        default=None, description="Units exactly as the customer stated; null if not stated"
    )
    specs: list[Spec] = Field(default_factory=list)
    notes: str | None = Field(
        default=None, description="Anything relevant that doesn't fit a spec, verbatim"
    )

    def spec_dict(self) -> dict[str, str]:
        return {s.name: s.value for s in self.specs}


class Extraction(BaseModel):
    items: list[ExtractedItem] = Field(default_factory=list)
    delivery_by: str | None = Field(default=None, description="Delivery phrase as written")
    customer_state: str | None = Field(
        default=None, description="Indian state or UT the customer mentions, as written"
    )


class IntentResult(BaseModel):
    intent: Literal["new_quote", "cancel", "other"] = Field(
        description="new_quote: asks for a price or wants to order items (including adding "
        "details to an earlier request). cancel: wants to cancel an order or quote. "
        "other: anything else."
    )
    reason: str = Field(description="One short sentence explaining the choice")
