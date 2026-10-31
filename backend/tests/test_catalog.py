import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.schemas.pricing import Catalog, CatalogItem
from app.services.catalog import CatalogError, load_catalog


def item_dict(**overrides: object) -> dict:
    base = {
        "sku": "TEE",
        "name": "Tee",
        "category": "apparel",
        "hsn": "6109",
        "unit": "pc",
        "base_price_paise": 20000,
        "gst": {"type": "flat", "rate_bp": 500},
    }
    return base | overrides


def test_seed_catalog_is_valid() -> None:
    catalog = load_catalog()
    assert len(catalog.items) >= 10
    assert {i.category for i in catalog.items} >= {"apparel", "fabrication", "carpentry"}
    assert catalog.get("TEE-RN-BLK") is not None
    assert catalog.get("NOPE") is None


async def test_app_loads_catalog_at_startup(app: FastAPI) -> None:
    assert isinstance(app.state.catalog, Catalog)


def test_duplicate_skus_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate SKUs: TEE"):
        Catalog.model_validate({"items": [item_dict(), item_dict()]})


def test_tiers_must_ascend() -> None:
    tiers = [{"min_qty": 200, "price_paise": 1}, {"min_qty": 50, "price_paise": 2}]
    with pytest.raises(ValidationError, match="strictly ascending"):
        CatalogItem.model_validate(item_dict(tiers=tiers))


@pytest.mark.parametrize(
    ("slabs", "message"),
    [
        ([{"max_unit_price_paise": 100, "rate_bp": 500}], "must be open-ended"),
        ([{"rate_bp": 500}, {"rate_bp": 1800}], "only the last"),
        (
            [
                {"max_unit_price_paise": 200, "rate_bp": 500},
                {"max_unit_price_paise": 100, "rate_bp": 1200},
                {"rate_bp": 1800},
            ],
            "strictly ascending",
        ),
    ],
)
def test_bad_gst_slabs_rejected(slabs: list[dict], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        CatalogItem.model_validate(item_dict(gst={"type": "slab", "slabs": slabs}))


def test_surcharge_spec_must_be_required() -> None:
    with pytest.raises(ValidationError, match="must be in required_specs"):
        CatalogItem.model_validate(item_dict(spec_surcharges={"print_type": {"dtf": 3000}}))


def test_surcharge_options_must_be_lowercase() -> None:
    with pytest.raises(ValidationError, match="must be lowercase"):
        CatalogItem.model_validate(
            item_dict(required_specs=["print_type"], spec_surcharges={"print_type": {"DTF": 1}})
        )


def test_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        CatalogItem.model_validate(item_dict(price=100))


def test_missing_file_raises_catalog_error(tmp_path: Path) -> None:
    with pytest.raises(CatalogError, match="cannot read catalog"):
        load_catalog(tmp_path / "missing.json")


def test_invalid_file_raises_catalog_error(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"items": [item_dict(hsn="abc")]}), encoding="utf-8")
    with pytest.raises(CatalogError, match="invalid catalog"):
        load_catalog(path)
