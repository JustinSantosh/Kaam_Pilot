import random

import pytest

from app.schemas.pricing import Catalog, CatalogItem, Discount, PricingInput
from app.services.money import paise_to_display
from app.services.pricing import (
    FLAG_STATE_UNKNOWN,
    PricingError,
    allocate_discount,
    price_quote,
)

APPAREL_SLABS = {
    "type": "slab",
    "slabs": [{"max_unit_price_paise": 250000, "rate_bp": 500}, {"rate_bp": 1800}],
}


def make_item(**overrides: object) -> CatalogItem:
    base = {
        "sku": "TEE",
        "name": "Tee",
        "category": "apparel",
        "hsn": "6109",
        "unit": "pc",
        "base_price_paise": 22000,
        "tiers": [{"min_qty": 50, "price_paise": 20000}, {"min_qty": 200, "price_paise": 18000}],
        "moq": 20,
        "setup_fee_paise": 50000,
        "required_specs": ["print_type"],
        "spec_surcharges": {"print_type": {"screen": 0, "dtf": 3000, "embroidery": 6000}},
        "gst": APPAREL_SLABS,
    }
    return CatalogItem.model_validate(base | overrides)


def plain_item(sku: str, price: int, gst: dict | None = None) -> CatalogItem:
    """No tiers, MOQ 1, no setup fee, no surcharges: isolates the tax maths."""
    return make_item(
        sku=sku,
        base_price_paise=price,
        tiers=[],
        moq=1,
        setup_fee_paise=0,
        required_specs=[],
        spec_surcharges={},
        gst=gst or {"type": "flat", "rate_bp": 500},
    )


CATALOG = Catalog(
    items=[
        make_item(),
        make_item(
            sku="GATE",
            category="fabrication",
            hsn="7308",
            unit="sqft",
            base_price_paise=45000,
            tiers=[],
            moq=1,
            setup_fee_paise=150000,
            required_specs=[],
            spec_surcharges={},
            gst={"type": "flat", "rate_bp": 1800},
        ),
        plain_item("AT-SLAB", 250000, APPAREL_SLABS),
        plain_item("OVER-SLAB", 250001, APPAREL_SLABS),
        plain_item("SMALL-A", 1010),
        plain_item("SMALL-B", 1010),
    ]
)


def quote(*lines: PricingInput, state: str | None = "CG", discount: Discount | None = None):
    return price_quote(
        lines, catalog=CATALOG, business_state="CG", customer_state=state, discount=discount
    )


def tee(qty: int, print_type: str = "screen") -> PricingInput:
    return PricingInput(sku="TEE", quantity=qty, specs={"print_type": print_type})


# --- unit price -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("qty", "unit"), [(20, 22000), (49, 22000), (50, 20000), (199, 20000), (200, 18000)]
)
def test_tier_boundaries(qty: int, unit: int) -> None:
    assert quote(tee(qty)).lines[0].unit_price_paise == unit


def test_below_moq_raises() -> None:
    with pytest.raises(PricingError, match="below MOQ 20"):
        quote(tee(19))


@pytest.mark.parametrize(("print_type", "unit"), [("dtf", 23000), ("embroidery", 26000)])
def test_surcharges_add_to_tier_price(print_type: str, unit: int) -> None:
    assert quote(tee(50, print_type)).lines[0].unit_price_paise == unit


def test_surcharge_option_is_case_insensitive() -> None:
    assert quote(tee(50, "  DTF ")).lines[0].unit_price_paise == 23000


def test_missing_price_affecting_spec_raises() -> None:
    with pytest.raises(PricingError, match="'print_type' is needed"):
        quote(PricingInput(sku="TEE", quantity=50))


def test_unknown_spec_option_raises() -> None:
    with pytest.raises(PricingError, match="unknown print_type 'vinyl'"):
        quote(tee(50, "vinyl"))


def test_unknown_sku_and_empty_quote_raise() -> None:
    with pytest.raises(PricingError, match="unknown SKU"):
        quote(PricingInput(sku="NOPE", quantity=1))
    with pytest.raises(PricingError, match="nothing to price"):
        quote()


def test_setup_fee_once_per_line() -> None:
    line = quote(tee(50)).lines[0]
    assert line.line_subtotal_paise == 20000 * 50 + 50000


# --- GST rate and place of supply -----------------------------------------------------------------


def test_slab_boundary_is_inclusive() -> None:
    at, over = quote(
        PricingInput(sku="AT-SLAB", quantity=1), PricingInput(sku="OVER-SLAB", quantity=1)
    ).lines
    assert at.gst_rate_bp == 500
    assert over.gst_rate_bp == 1800


def test_slab_uses_post_discount_unit_value() -> None:
    line = quote(
        PricingInput(sku="OVER-SLAB", quantity=1), discount=Discount(kind="flat", value=1)
    ).lines[0]
    assert line.taxable_paise == 250000
    assert line.gst_rate_bp == 500


def test_intra_state_splits_cgst_sgst() -> None:
    q = quote(tee(50), state="cg")
    line = q.lines[0]
    assert q.supply_type == "intra_state"
    assert line.cgst_paise == line.sgst_paise == 26250  # 2.5% of 10,50,000 paise
    assert line.igst_paise == 0
    assert q.flags == []


def test_inter_state_uses_igst() -> None:
    q = quote(tee(50), state="MH")
    line = q.lines[0]
    assert q.supply_type == "inter_state"
    assert (line.cgst_paise, line.sgst_paise, line.igst_paise) == (0, 0, 52500)


@pytest.mark.parametrize("state", [None, "", "  "])
def test_unknown_state_assumes_intra_and_flags(state: str | None) -> None:
    q = quote(tee(50), state=state)
    assert q.supply_type == "intra_state"
    assert q.flags == [FLAG_STATE_UNKNOWN]


# --- rounding -------------------------------------------------------------------------------------


def test_tax_is_rounded_per_line_not_per_quote() -> None:
    # 2.5% of 1010 = 25.25 → 25 per line, so 50 in total; rounding the quote would give 51.
    q = quote(PricingInput(sku="SMALL-A", quantity=1), PricingInput(sku="SMALL-B", quantity=1))
    assert [ln.cgst_paise for ln in q.lines] == [25, 25]
    assert q.totals.cgst_paise == 50


def test_half_paisa_rounds_up() -> None:
    # 5% of 1010 = 50.5 → 51
    q = quote(PricingInput(sku="SMALL-A", quantity=1), state="MH")
    assert q.lines[0].igst_paise == 51


# --- discounts ------------------------------------------------------------------------------------


def test_percent_discount() -> None:
    q = quote(tee(50), discount=Discount(kind="percent", value=1000))
    assert q.totals.discount_paise == 105000
    assert q.totals.taxable_paise == 1050000 - 105000


def test_flat_discount_larger_than_subtotal_raises() -> None:
    with pytest.raises(PricingError, match="larger than the quote subtotal"):
        quote(PricingInput(sku="SMALL-A", quantity=1), discount=Discount(kind="flat", value=1011))


def test_percent_over_100_rejected() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        Discount(kind="percent", value=10001)


def test_discount_spread_proportionally_with_exact_sum() -> None:
    q = quote(
        tee(50),
        PricingInput(sku="GATE", quantity=30),
        discount=Discount(kind="flat", value=10001),
    )
    shares = [ln.discount_paise for ln in q.lines]
    assert sum(shares) == 10001
    # Exact shares 4118.06… and 5882.94…: floors sum to 10000, the leftover paisa goes to .94
    assert shares == [4118, 5883]


@pytest.mark.parametrize(
    ("subtotals", "discount", "expected"),
    [
        ([100, 100, 100], 100, [34, 33, 33]),  # tie on fractions → earlier line wins
        ([1, 1, 1], 2, [1, 1, 0]),  # leftover never pushes a line past its subtotal
        ([500, 300], 0, [0, 0]),
        ([500, 300], 800, [500, 300]),
    ],
)
def test_allocate_discount(subtotals: list[int], discount: int, expected: list[int]) -> None:
    assert allocate_discount(subtotals, discount) == expected


# --- invariants over random carts -----------------------------------------------------------------


@pytest.mark.parametrize("seed", range(200))
def test_random_cart_invariants(seed: int) -> None:
    rng = random.Random(seed)
    lines = []
    for _ in range(rng.randint(1, 4)):
        if rng.random() < 0.5:
            lines.append(tee(rng.randint(20, 400), rng.choice(["screen", "dtf", "embroidery"])))
        else:
            lines.append(PricingInput(sku="GATE", quantity=rng.randint(1, 300)))
    discount = rng.choice(
        [
            None,
            Discount(kind="percent", value=rng.randint(0, 5000)),
            Discount(kind="flat", value=rng.randint(0, 50000)),
        ]
    )
    q = quote(*lines, state=rng.choice(["CG", "MH", None]), discount=discount)
    t = q.totals

    for ln in q.lines:
        assert 0 <= ln.discount_paise <= ln.line_subtotal_paise
        assert ln.taxable_paise == ln.line_subtotal_paise - ln.discount_paise
        assert (
            ln.line_total_paise == ln.taxable_paise + ln.cgst_paise + ln.sgst_paise + ln.igst_paise
        )
        assert ln.cgst_paise == ln.sgst_paise
    assert t.subtotal_paise == sum(ln.line_subtotal_paise for ln in q.lines)
    assert t.taxable_paise == t.subtotal_paise - t.discount_paise
    assert t.tax_paise == t.cgst_paise + t.sgst_paise + t.igst_paise
    assert t.total_paise == t.taxable_paise + t.tax_paise
    if q.supply_type == "inter_state":
        assert t.cgst_paise == t.sgst_paise == 0
    else:
        assert t.igst_paise == 0


# --- display --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("paise", "text"),
    [
        (0, "₹0.00"),
        (99, "₹0.99"),
        (123456, "₹1,234.56"),
        (10000000, "₹1,00,000.00"),
        (123900050, "₹12,39,000.50"),
        (1234567890, "₹1,23,45,678.90"),
        (-5000, "-₹50.00"),
    ],
)
def test_paise_to_display(paise: int, text: str) -> None:
    assert paise_to_display(paise) == text
