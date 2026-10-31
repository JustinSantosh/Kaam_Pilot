# Phase 02: Catalog & deterministic pricing

- **Status:** Done (pending commit)
- **Depends on:** [01](phase-01.md)
- **Decisions:** [D-002](../decisions.md#d-002), [D-005](../decisions.md#d-005), [D-006](../decisions.md#d-006), [D-018](../decisions.md#d-018)

## Goal
Pure, fully tested pricing: given matched catalog items and quantities, produce priced line items and
totals that are correct to the paisa, with the right GST split. No LLM anywhere in this phase.

## Scope
**In:** `catalog.json` format + seed data, catalog loader/validator, pricing engine, discount
application, GST slab and place-of-supply logic, exhaustive unit tests.
**Out:** matching free text to SKUs (Phase 03), persistence (Phase 04).

## Deliverables
```
backend/app/data/catalog.json
backend/app/schemas/pricing.py     # Catalog, CatalogItem, PricingInput, Discount, PricedLineItem, QuoteTotals, PricedQuote
backend/app/services/catalog.py    # load_catalog() → validated, cached; loaded in app lifespan
backend/app/services/money.py      # round_paise, apply_bp, paise_to_display
backend/app/services/pricing.py    # price_quote(...) → PricedQuote
backend/tests/test_catalog.py
backend/tests/test_pricing.py
```

## Catalog format (per item)
```json
{
  "sku": "TEE-RN-BLK",
  "name": "Round-neck cotton T-shirt (black)",
  "aliases": ["black tee", "kaali t-shirt", "round neck black"],
  "category": "apparel",
  "hsn": "6109",
  "unit": "pc",
  "base_price_paise": 22000,
  "tiers": [{"min_qty": 50, "price_paise": 20000}, {"min_qty": 200, "price_paise": 18000}],
  "moq": 20,
  "setup_fee_paise": 50000,
  "required_specs": ["size_mix", "print_type", "placement"],
  "spec_surcharges": {"print_type": {"screen": 0, "dtf": 3000, "embroidery": 6000}},
  "gst": {"type": "slab", "slabs": [{"max_unit_price_paise": 250000, "rate_bp": 500},
                                     {"rate_bp": 1800}]}
}
```
Seed rates are illustrative only; the owner verifies them for their own goods ([D-006](../decisions.md#d-006)).
Seed ~10 items across apparel, fabrication and carpentry so later evals have variety.

## Pricing rules (written down, then tested)
1. Unit price = applicable tier price (highest `min_qty` ≤ qty) + spec surcharges. A spec with
   surcharges must be in `required_specs` (the catalog loader enforces it), and pricing raises if
   it's missing or has an unknown option (case-insensitive match).
2. Quantity < MOQ → `PricingError` (validation in Phase 03 should catch it first; this is the backstop).
3. Line subtotal = unit × qty + setup fee.
4. Discount (owner-applied, Phase 05) reduces the taxable value, spread over lines in proportion to
   their subtotal; leftover paise go one each to the lines with the largest fractional share
   ([D-018](../decisions.md#d-018)). Flat discount > subtotal raises.
5. GST rate per line from slab using the **post-discount unit value** (taxable ÷ qty, so setup fee
   is included). A value exactly at a slab's max is in that slab.
6. Tax per line, `ROUND_HALF_UP` to paise. Intra-state: CGST = SGST = half the rate, each rounded.
   Inter-state: IGST at the full rate.
7. Totals = sum of lines; total = taxable + tax.

## Tasks
- [x] Pydantic `CatalogItem` with validators (tiers sorted, slabs end with an open slab, SKUs unique).
- [x] `load_catalog()` fails fast on invalid catalog at startup.
- [x] `price_quote(items, *, catalog, business_state, customer_state, discount) -> PricedQuote`.
- [x] Helper `paise_to_display()` for templates (backend only; frontend has its own).
- [x] Table-driven tests (pytest `parametrize`).

## Exit criteria
Tests cover and pass:
- each tier boundary (49/50/199/200);
- MOQ violation raises;
- surcharges stack;
- setup fee once per line;
- GST slab boundary exactly at the threshold;
- intra-state vs inter-state split, and unknown state → intra + flag;
- rounding: a case where per-line rounding differs from rounding the total (documents the rule);
- discount spread with remainder paise;
- totals equal the sum of lines (property-style test over random carts).

## Risks / open questions
- Per-line vs per-invoice tax rounding: per-line is chosen for clarity. Confirm against the owner's
  accountant before real use.
- Setup fee taxed at the item's rate (assumed). Check this.
- Including the setup fee in the per-unit value for GST slabs can push small apparel orders into a
  higher slab. That's conservative, but confirm it with the accountant.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-10-31: implemented. Seed catalog has 10 items (apparel, fabrication, carpentry, printing).
  249 new tests (251 total), including 200 seeded random carts that check the totals add up.
  `ruff` clean; server boots with the catalog loaded. Changes from the original plan:
  dropped `setup_fee_per` (always once per line); discount leftovers use the largest-remainder
  method instead of "largest line", because the original rule could push a tiny line's discount
  above its own subtotal ([D-018](../decisions.md#d-018)).
