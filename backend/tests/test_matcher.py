import pytest

from app.services.catalog import load_catalog
from app.services.matcher import match, normalize

CATALOG = load_catalog()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Black T-Shirts!", "black tshirt"),
        ("t shirt", "tshirt"),
        ("tees", "tshirt"),
        ("glass railings", "glass railing"),
        ("  ", ""),
    ],
)
def test_normalize(text: str, expected: str) -> None:
    assert normalize(text) == expected


@pytest.mark.parametrize(
    ("text", "sku"),
    [
        ("kaali t-shirt", "TEE-RN-BLK"),  # alias
        ("black round-neck t-shirt", "TEE-RN-BLK"),
        ("black tshirts", "TEE-RN-BLK"),
        ("white tee", "TEE-RN-WHT"),
        ("collar tshirt", "POLO-NVY"),
        ("black hoodie", "HOOD-BLK"),
        ("loha gate", "GATE-MS"),
        ("balcony railing", "RAIL-SS"),
        ("almirah", "WARD-LAM"),
        ("modular kitchen", "KIT-BASE"),
        ("flex banner", "FLEX-BNR"),
        ("blak tshirt", "TEE-RN-BLK"),  # typo
        ("wardobe", "WARD-LAM"),  # typo
    ],
)
def test_matches(text: str, sku: str) -> None:
    result = match(text, CATALOG)
    assert result.status == "matched"
    assert result.sku == sku


@pytest.mark.parametrize(
    ("text", "includes"),
    [
        ("t-shirt", {"TEE-RN-BLK", "TEE-RN-WHT"}),
        ("black", {"TEE-RN-BLK", "HOOD-BLK"}),
        ("round neck tshirt", {"TEE-RN-BLK", "TEE-RN-WHT"}),
    ],
)
def test_ambiguous_offers_candidates(text: str, includes: set[str]) -> None:
    result = match(text, CATALOG)
    assert result.status == "ambiguous"
    assert result.sku is None
    assert includes <= {c.sku for c in result.candidates}
    assert len(result.candidates) <= 3


@pytest.mark.parametrize("text", ["coffee mug", "", "!!!"])
def test_no_match(text: str) -> None:
    result = match(text, CATALOG)
    assert result.status == "none"
    assert result.candidates == ()
