import pytest

from app.schemas.extraction import ExtractedItem, Extraction, Spec
from app.services.catalog import load_catalog
from app.services.clarify import GREETING, NO_ITEMS, clarify_message
from app.services.validator import validate

CATALOG = load_catalog()


def message(*items: ExtractedItem) -> str:
    return clarify_message(validate(Extraction(items=list(items)), CATALOG), CATALOG)


def test_asks_exactly_for_missing_specs_with_options() -> None:
    text = message(
        ExtractedItem(
            item_text="black tee",
            quantity=40,
            specs=[Spec(name="placement", value="front"), Spec(name="print_type", value="dtf")],
        )
    )
    assert text == (
        f"{GREETING}\n"
        "- Round-neck cotton T-shirt (black): sizes and how many of each (e.g. M:10, L:15)"
    )


def test_ambiguous_lists_product_names() -> None:
    text = message(ExtractedItem(item_text="t-shirt", quantity=50))
    assert '"t-shirt": which one do you mean:' in text
    assert "Round-neck cotton T-shirt (black)" in text
    assert "Round-neck cotton T-shirt (white)" in text


def test_complete_items_are_not_mentioned() -> None:
    text = message(
        ExtractedItem(
            item_text="black hoodie",
            quantity=50,
            specs=[
                Spec(name="size_mix", value="M:50"),
                Spec(name="print_type", value="dtf"),
                Spec(name="placement", value="back"),
            ],
        ),
        ExtractedItem(item_text="ss railing", specs=[Spec(name="length_rft", value="24")]),
    )
    assert "hoodie" not in text
    assert "Stainless steel railing (SS 304): glass (none, toughened 12mm or toughened 8mm)" in text


def test_quantity_and_moq_questions_use_units() -> None:
    assert "how many pc?" in message(ExtractedItem(item_text="black hoodie"))
    assert "our minimum is 10 pc" in message(ExtractedItem(item_text="black hoodie", quantity=3))


def test_unmatched_and_no_items() -> None:
    assert "couldn't find this" in message(ExtractedItem(item_text="coffee mug", quantity=5))
    assert clarify_message(validate(Extraction(), CATALOG), CATALOG) == NO_ITEMS


def test_refuses_complete_result() -> None:
    complete = validate(
        Extraction(
            items=[
                ExtractedItem(
                    item_text="ms gate",
                    specs=[
                        Spec(name="width_ft", value="12"),
                        Spec(name="height_ft", value="6"),
                        Spec(name="design", value="simple"),
                        Spec(name="finish", value="primer"),
                    ],
                )
            ]
        ),
        CATALOG,
    )
    with pytest.raises(ValueError, match="nothing to clarify"):
        clarify_message(complete, CATALOG)
