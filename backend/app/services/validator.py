"""Decide in code whether an extraction is complete enough to price (D-004).

The LLM only says what the customer wrote. This module decides what's missing, using catalog
rules the owner controls: SKU match, quantity, MOQ, required specs and allowed spec options.
"""

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.extraction import Extraction
from app.schemas.pricing import Catalog, CatalogItem, PricingInput
from app.services.matcher import match

IssueCode = Literal[
    "no_items",
    "unmatched",
    "ambiguous",
    "missing_quantity",
    "below_moq",
    "missing_spec",
    "invalid_option",
]


class Issue(BaseModel):
    code: IssueCode
    field: str | None = None
    message: str
    options: list[str] = Field(default_factory=list)  # SKUs or allowed spec values


class ValidatedItem(BaseModel):
    index: int
    item_text: str
    sku: str | None
    name: str | None
    quantity: int | None
    specs: dict[str, str]
    issues: list[Issue] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # shown to the owner, e.g. derived quantities

    @property
    def complete(self) -> bool:
        return not self.issues


class ValidationResult(BaseModel):
    complete: bool
    items: list[ValidatedItem]
    issues: list[Issue] = Field(default_factory=list)  # quote-level issues

    def pricing_inputs(self) -> list[PricingInput]:
        if not self.complete:
            raise ValueError("cannot price an incomplete extraction")
        return [
            PricingInput(sku=i.sku, quantity=i.quantity, specs=i.specs)  # type: ignore[arg-type]
            for i in self.items
        ]


def normalize_spec_name(name: str) -> str:
    return "_".join(name.strip().lower().replace("-", " ").split())


def normalize_option(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", " ").split())


def _clean_specs(raw: dict[str, str], item: CatalogItem | None) -> dict[str, str]:
    specs = {}
    for name, value in raw.items():
        key, val = normalize_spec_name(name), value.strip()
        if not val:
            continue
        if item is not None and key in item.spec_surcharges:
            val = normalize_option(val)
        specs[key] = val
    return specs


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _number(value: str | None) -> Decimal | None:
    found = _NUMBER.search(value or "")
    if not found:
        return None
    try:
        number = Decimal(found.group())
    except InvalidOperation:
        return None
    return number if number > 0 else None


def _derive_quantity(
    item: CatalogItem, count: int | None, specs: dict[str, str]
) -> tuple[int | None, str | None]:
    """For area/length units, compute the billable quantity from dimensions in code (D-002).

    When dimensions are given, the customer's number is a count of pieces (default 1):
    "2 wardrobes 8x7 ft" is 2 × 56 = 112 sqft. Without dimensions the number is used as is.
    """
    pieces = count or 1
    if item.unit == "sqft":
        width, height = _number(specs.get("width_ft")), _number(specs.get("height_ft"))
        if width and height:
            qty = math.ceil(pieces * width * height)
            return qty, f"{qty} sqft = {pieces} × {width} ft × {height} ft (rounded up)"
    if item.unit == "rft":
        length = _number(specs.get("length_rft"))
        if length:
            qty = math.ceil(pieces * length)
            return qty, f"{qty} rft = {pieces} × {length} ft (rounded up)"
    return count, None


def _check_item(
    index: int, text: str, quantity: int | None, raw_specs: dict[str, str], catalog: Catalog
) -> ValidatedItem:
    result = match(text, catalog)
    item = catalog.get(result.sku) if result.sku else None
    specs = _clean_specs(raw_specs, item)
    issues: list[Issue] = []
    notes: list[str] = []
    if item is not None:
        quantity, note = _derive_quantity(item, quantity, specs)
        if note:
            notes.append(note)

    if result.status == "none":
        issues.append(Issue(code="unmatched", message=f"no catalog item matches '{text}'"))
    elif result.status == "ambiguous":
        issues.append(
            Issue(
                code="ambiguous",
                message=f"'{text}' could be several catalog items",
                options=[c.sku for c in result.candidates],
            )
        )

    if quantity is None:
        issues.append(Issue(code="missing_quantity", field="quantity", message="quantity missing"))
    elif item is not None and quantity < item.moq:
        issues.append(
            Issue(
                code="below_moq",
                field="quantity",
                message=f"minimum order for {item.name} is {item.moq} {item.unit}",
            )
        )

    if item is not None:
        for spec in item.required_specs:
            if spec not in specs:
                allowed = sorted(item.spec_surcharges.get(spec, {}))
                issues.append(
                    Issue(
                        code="missing_spec", field=spec, message=f"{spec} missing", options=allowed
                    )
                )
            elif spec in item.spec_surcharges and specs[spec] not in item.spec_surcharges[spec]:
                allowed = sorted(item.spec_surcharges[spec])
                issues.append(
                    Issue(
                        code="invalid_option",
                        field=spec,
                        message=f"'{specs[spec]}' is not an option for {spec}",
                        options=allowed,
                    )
                )

    return ValidatedItem(
        index=index,
        item_text=text,
        sku=item.sku if item else None,
        name=item.name if item else None,
        quantity=quantity,
        specs=specs,
        issues=issues,
        notes=notes,
    )


def validate(extraction: Extraction, catalog: Catalog) -> ValidationResult:
    if not extraction.items:
        issue = Issue(code="no_items", message="the message doesn't name any product")
        return ValidationResult(complete=False, items=[], issues=[issue])
    items = [
        _check_item(i, x.item_text, x.quantity, x.spec_dict(), catalog)
        for i, x in enumerate(extraction.items)
    ]
    return ValidationResult(complete=all(i.complete for i in items), items=items)
