"""Live extraction against the golden inquiries. Opt-in: `pytest -m llm` with KP_LLM_MODEL and
the provider's API key set. Compares what matters after validation: SKUs, quantities, outcome."""

import pytest

from app.config import get_settings
from app.llm.functions import extract
from app.services.catalog import load_catalog
from app.services.validator import validate
from tests.golden import load_golden

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not get_settings().llm_model, reason="KP_LLM_MODEL not set"),
]

CATALOG = load_catalog()


@pytest.mark.parametrize("case", load_golden(), ids=lambda c: c["id"])
async def test_golden_live(case: dict) -> None:
    extraction = await extract(case["input"], catalog=CATALOG)
    result = validate(extraction, CATALOG)
    expected = case["expected"]

    got = sorted((i.sku or "", i.quantity or 0) for i in result.items)
    want = sorted((i["sku"] or "", i["quantity"] or 0) for i in expected["items"])
    assert got == want
    assert result.complete == expected["complete"]
