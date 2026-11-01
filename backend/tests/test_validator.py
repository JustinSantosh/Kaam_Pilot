import pytest

from app.schemas.extraction import ExtractedItem, Extraction, Spec
from app.services.catalog import load_catalog
from app.services.pricing import price_quote
from app.services.validator import ValidationResult, validate
from tests.golden import load_golden

CATALOG = load_catalog()


def one(text: str, quantity: int | None = None, **specs: str) -> ValidationResult:
    item = ExtractedItem(
        item_text=text,
        quantity=quantity,
        specs=[Spec(name=k, value=v) for k, v in specs.items()],
    )
    return validate(Extraction(items=[item]), CATALOG)


def codes(result: ValidationResult) -> list[tuple[str, str | None]]:
    return [(i.code, i.field) for item in result.items for i in item.issues]


TEE_SPECS = {"size_mix": "M:20, L:30", "print_type": "screen", "placement": "front"}


def test_complete_item() -> None:
    result = one("black tee", 50, **TEE_SPECS)
    assert result.complete
    assert result.pricing_inputs()[0].model_dump() == {
        "sku": "TEE-RN-BLK",
        "quantity": 50,
        "specs": TEE_SPECS,
    }


def test_no_items() -> None:
    result = validate(Extraction(items=[]), CATALOG)
    assert not result.complete
    assert [i.code for i in result.issues] == ["no_items"]


def test_missing_quantity() -> None:
    assert codes(one("black tee", None, **TEE_SPECS)) == [("missing_quantity", "quantity")]


def test_below_moq() -> None:
    assert codes(one("black tee", 10, **TEE_SPECS)) == [("below_moq", "quantity")]


def test_missing_specs_listed_with_options() -> None:
    result = one("black tee", 50, size_mix="M:50")
    assert codes(result) == [("missing_spec", "print_type"), ("missing_spec", "placement")]
    print_issue = result.items[0].issues[0]
    assert print_issue.options == ["dtf", "embroidery", "screen"]


def test_spec_names_and_options_are_normalized() -> None:
    result = one(
        "ms gate",
        None,
        **{"Width FT": "12", "height-ft": "6", "design": "simple", "finish": "Powder Coat"},
    )
    assert result.complete
    assert result.items[0].specs["finish"] == "powder_coat"


def test_invalid_option() -> None:
    result = one("black tee", 50, size_mix="M:50", print_type="vinyl", placement="front")
    assert codes(result) == [("invalid_option", "print_type")]


def test_unmatched_and_ambiguous_skip_spec_checks() -> None:
    assert codes(one("coffee mug", 100)) == [("unmatched", None)]
    ambiguous = one("t-shirt", 50)
    assert codes(ambiguous) == [("ambiguous", None)]
    assert {"TEE-RN-BLK", "TEE-RN-WHT"} <= set(ambiguous.items[0].issues[0].options)


def test_pricing_inputs_refused_when_incomplete() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        one("t-shirt", 50).pricing_inputs()


# --- quantity derived from dimensions -------------------------------------------------------------


@pytest.mark.parametrize(
    ("count", "width", "height", "expected"),
    [(None, "12", "6", 72), (2, "8", "7", 112), (1, "10.5 ft", "4", 42), (None, "7.3", "3.1", 23)],
)
def test_area_quantity(count: int | None, width: str, height: str, expected: int) -> None:
    result = one("ms gate", count, width_ft=width, height_ft=height, design="x", finish="primer")
    item = result.items[0]
    assert item.quantity == expected
    assert item.notes and item.notes[0].startswith(f"{expected} sqft")


def test_length_quantity() -> None:
    item = one("ss railing", None, length_rft="24 running feet", glass="none").items[0]
    assert item.quantity == 24
    assert item.issues == []


def test_count_kept_without_dimensions() -> None:
    item = one("ms gate", 40, design="x", finish="primer").items[0]
    assert item.quantity == 40
    assert ("missing_spec", "width_ft") in [(i.code, i.field) for i in item.issues]


# --- golden inquiries, offline: ideal extraction → validation -------------------------------------


@pytest.mark.parametrize("case", load_golden(), ids=lambda c: c["id"])
def test_golden_validation(case: dict) -> None:
    result = validate(Extraction.model_validate(case["ideal_extraction"]), CATALOG)
    expected = case["expected"]
    assert result.complete == expected["complete"]
    for item, want in zip(result.items, expected["items"], strict=True):
        assert item.sku == want["sku"]
        assert item.quantity == want["quantity"]
        missing = [i.field for i in item.issues if i.code == "missing_spec"]
        assert missing == want["missing"]
    if result.complete:
        quote = price_quote(
            result.pricing_inputs(), catalog=CATALOG, business_state="CG", customer_state="CG"
        )
        assert quote.totals.total_paise > 0
