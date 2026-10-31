"""Catalog and pricing models. Money is integer paise, rates integer basis points (D-005)."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

# --- Catalog --------------------------------------------------------------------------------------


class Tier(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_qty: int = Field(gt=0)
    price_paise: int = Field(ge=0)


class FlatGst(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["flat"]
    rate_bp: int = Field(ge=0, le=10000)

    def rate_for(self, unit_value_paise: Decimal) -> int:
        return self.rate_bp


class GstSlab(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_unit_price_paise: int | None = Field(default=None, gt=0)  # None = open-ended top slab
    rate_bp: int = Field(ge=0, le=10000)


class SlabGst(BaseModel):
    """Rate depends on taxable value per unit; a value exactly at a slab's max is in that slab."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["slab"]
    slabs: list[GstSlab] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_slabs(self) -> Self:
        *bounded, top = self.slabs
        if top.max_unit_price_paise is not None:
            raise ValueError("the last GST slab must be open-ended (no max_unit_price_paise)")
        maxes = [s.max_unit_price_paise for s in bounded]
        if any(m is None for m in maxes):
            raise ValueError("only the last GST slab may be open-ended")
        if maxes != sorted(set(maxes)):
            raise ValueError("GST slab maxima must be strictly ascending")
        return self

    def rate_for(self, unit_value_paise: Decimal) -> int:
        for slab in self.slabs:
            if slab.max_unit_price_paise is None or unit_value_paise <= slab.max_unit_price_paise:
                return slab.rate_bp
        raise AssertionError("unreachable: last slab is open-ended")


GstRule = Annotated[FlatGst | SlabGst, Field(discriminator="type")]


class CatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sku: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]*$")
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    category: str
    hsn: str = Field(pattern=r"^\d{4,8}$")
    unit: str = Field(min_length=1)
    base_price_paise: int = Field(ge=0)
    tiers: list[Tier] = Field(default_factory=list)
    moq: int = Field(default=1, gt=0)
    setup_fee_paise: int = Field(default=0, ge=0)
    required_specs: list[str] = Field(default_factory=list)
    spec_surcharges: dict[str, dict[str, int]] = Field(default_factory=dict)
    gst: GstRule

    @model_validator(mode="after")
    def _check_item(self) -> Self:
        mins = [t.min_qty for t in self.tiers]
        if mins != sorted(set(mins)):
            raise ValueError(f"{self.sku}: tier min_qty values must be strictly ascending")
        for spec, options in self.spec_surcharges.items():
            # A spec that changes the price must be asked for, or pricing can't run.
            if spec not in self.required_specs:
                raise ValueError(f"{self.sku}: surcharge spec '{spec}' must be in required_specs")
            for option, amount in options.items():
                if option != option.strip().lower():
                    raise ValueError(f"{self.sku}: option '{option}' must be lowercase, no padding")
                if amount < 0:
                    raise ValueError(f"{self.sku}: surcharge for '{option}' must be >= 0")
        return self

    def tier_price_for(self, quantity: int) -> int:
        price = self.base_price_paise
        for tier in self.tiers:
            if quantity >= tier.min_qty:
                price = tier.price_paise
        return price


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int = 1
    currency: Literal["INR"] = "INR"
    note: str = ""
    items: list[CatalogItem] = Field(min_length=1)

    _by_sku: dict[str, CatalogItem] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        skus = [i.sku for i in self.items]
        dupes = sorted({s for s in skus if skus.count(s) > 1})
        if dupes:
            raise ValueError(f"duplicate SKUs: {', '.join(dupes)}")
        return self

    def model_post_init(self, context: object) -> None:
        self._by_sku = {i.sku: i for i in self.items}

    def get(self, sku: str) -> CatalogItem | None:
        return self._by_sku.get(sku)


# --- Pricing inputs -------------------------------------------------------------------------------


class PricingInput(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    specs: dict[str, str] = Field(default_factory=dict)


class Discount(BaseModel):
    """Owner-applied discount (D-009). `value` is paise for flat, basis points for percent."""

    kind: Literal["flat", "percent"]
    value: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_percent(self) -> Self:
        if self.kind == "percent" and self.value > 10000:
            raise ValueError("percent discount cannot exceed 10000 bp (100%)")
        return self


# --- Pricing outputs ------------------------------------------------------------------------------

SupplyType = Literal["intra_state", "inter_state"]


class PricedLineItem(BaseModel):
    sku: str
    name: str
    hsn: str
    unit: str
    quantity: int
    specs: dict[str, str]
    unit_price_paise: int  # tier price + spec surcharges
    setup_fee_paise: int
    line_subtotal_paise: int  # unit_price * quantity + setup_fee
    discount_paise: int  # this line's share of the quote discount
    taxable_paise: int  # line_subtotal - discount
    gst_rate_bp: int
    cgst_paise: int
    sgst_paise: int
    igst_paise: int
    line_total_paise: int  # taxable + all tax


class QuoteTotals(BaseModel):
    subtotal_paise: int
    discount_paise: int
    taxable_paise: int
    cgst_paise: int
    sgst_paise: int
    igst_paise: int
    tax_paise: int
    total_paise: int


class PricedQuote(BaseModel):
    lines: list[PricedLineItem]
    totals: QuoteTotals
    supply_type: SupplyType
    flags: list[str] = Field(default_factory=list)  # things the owner must look at
