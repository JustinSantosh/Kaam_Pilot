"""Deterministic quote pricing. No LLM ever touches this module (D-002).

Rules (docs/phases/phase-02.md):
1. Unit price = tier price for the quantity + surcharges for price-affecting specs.
2. Quantity below MOQ is an error.
3. Line subtotal = unit price × quantity + setup fee (once per line).
4. A quote discount is spread over lines in proportion to their subtotals; leftover paise go
   one each to the lines with the largest fractional shares (D-018).
5. GST rate comes from the item's rule, using the post-discount taxable value per unit.
6. Tax is rounded per line, half-up. Intra-state: CGST and SGST at half the rate each.
   Inter-state: IGST at the full rate (D-006).
7. Quote totals are sums of the line amounts.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.schemas.pricing import (
    Catalog,
    CatalogItem,
    Discount,
    PricedLineItem,
    PricedQuote,
    PricingInput,
    QuoteTotals,
    SupplyType,
)
from app.services.money import apply_bp

FLAG_STATE_UNKNOWN = "customer_state_unknown_assumed_intra_state"


class PricingError(ValueError):
    pass


def unit_price_paise(item: CatalogItem, quantity: int, specs: dict[str, str]) -> int:
    price = item.tier_price_for(quantity)
    for spec, options in item.spec_surcharges.items():
        value = specs.get(spec)
        if value is None:
            raise PricingError(f"{item.sku}: '{spec}' is needed to price this item")
        option = value.strip().lower()
        if option not in options:
            allowed = ", ".join(sorted(options))
            raise PricingError(f"{item.sku}: unknown {spec} '{value}' (allowed: {allowed})")
        price += options[option]
    return price


def discount_paise(discount: Discount | None, subtotal_paise: int) -> int:
    if discount is None:
        return 0
    if discount.kind == "percent":
        return apply_bp(subtotal_paise, discount.value)
    if discount.value > subtotal_paise:
        raise PricingError("flat discount is larger than the quote subtotal")
    return discount.value


def allocate_discount(subtotals: Sequence[int], discount: int) -> list[int]:
    """Split `discount` across lines in proportion to `subtotals`, exactly, never exceeding a line.

    Largest-remainder method: everyone gets the floor of their exact share, then the leftover
    paise go one each to the lines with the biggest fractional parts (earlier line wins a tie).
    """
    total = sum(subtotals)
    if not 0 <= discount <= total:
        raise PricingError("discount must be between 0 and the subtotal")
    if discount == 0:
        return [0] * len(subtotals)
    shares, fractions = [], []
    for i, subtotal in enumerate(subtotals):
        share, frac = divmod(discount * subtotal, total)
        shares.append(share)
        fractions.append((-frac, i))
    leftover = discount - sum(shares)
    for _, i in sorted(fractions)[:leftover]:
        shares[i] += 1
    return shares


def supply_type(business_state: str, customer_state: str | None) -> tuple[SupplyType, list[str]]:
    if not customer_state or not customer_state.strip():
        return "intra_state", [FLAG_STATE_UNKNOWN]
    same = customer_state.strip().upper() == business_state.strip().upper()
    return ("intra_state" if same else "inter_state"), []


def price_quote(
    items: Sequence[PricingInput],
    *,
    catalog: Catalog,
    business_state: str,
    customer_state: str | None,
    discount: Discount | None = None,
) -> PricedQuote:
    if not items:
        raise PricingError("nothing to price")

    supply, flags = supply_type(business_state, customer_state)

    prepared: list[tuple[PricingInput, CatalogItem, int, int]] = []
    for line in items:
        item = catalog.get(line.sku)
        if item is None:
            raise PricingError(f"unknown SKU '{line.sku}'")
        if line.quantity < item.moq:
            raise PricingError(f"{item.sku}: quantity {line.quantity} is below MOQ {item.moq}")
        unit = unit_price_paise(item, line.quantity, line.specs)
        prepared.append((line, item, unit, unit * line.quantity + item.setup_fee_paise))

    subtotals = [subtotal for *_, subtotal in prepared]
    shares = allocate_discount(subtotals, discount_paise(discount, sum(subtotals)))

    lines: list[PricedLineItem] = []
    for (line, item, unit, subtotal), share in zip(prepared, shares, strict=True):
        taxable = subtotal - share
        rate = item.gst.rate_for(Decimal(taxable) / line.quantity)
        if supply == "intra_state":
            cgst = sgst = apply_bp(taxable, Decimal(rate) / 2)
            igst = 0
        else:
            cgst = sgst = 0
            igst = apply_bp(taxable, rate)
        lines.append(
            PricedLineItem(
                sku=item.sku,
                name=item.name,
                hsn=item.hsn,
                unit=item.unit,
                quantity=line.quantity,
                specs=line.specs,
                unit_price_paise=unit,
                setup_fee_paise=item.setup_fee_paise,
                line_subtotal_paise=subtotal,
                discount_paise=share,
                taxable_paise=taxable,
                gst_rate_bp=rate,
                cgst_paise=cgst,
                sgst_paise=sgst,
                igst_paise=igst,
                line_total_paise=taxable + cgst + sgst + igst,
            )
        )

    cgst_total = sum(ln.cgst_paise for ln in lines)
    sgst_total = sum(ln.sgst_paise for ln in lines)
    igst_total = sum(ln.igst_paise for ln in lines)
    totals = QuoteTotals(
        subtotal_paise=sum(ln.line_subtotal_paise for ln in lines),
        discount_paise=sum(ln.discount_paise for ln in lines),
        taxable_paise=sum(ln.taxable_paise for ln in lines),
        cgst_paise=cgst_total,
        sgst_paise=sgst_total,
        igst_paise=igst_total,
        tax_paise=cgst_total + sgst_total + igst_total,
        total_paise=sum(ln.line_total_paise for ln in lines),
    )
    return PricedQuote(lines=lines, totals=totals, supply_type=supply, flags=flags)
