"""The eval harness itself (Phase 12): dataset integrity, metrics maths, ideal-mode gate."""

import json

import pytest

from evals.metrics import CaseResult, item_scores, outcome_ok, summarize
from evals.run_evals import DATASET, main

CASES = json.loads(DATASET.read_text(encoding="utf-8"))


def test_dataset_size_and_mix() -> None:
    assert len(CASES) >= 60
    assert len({c["id"] for c in CASES}) == len(CASES)
    categories = {c["category"] for c in CASES}
    assert {"clean", "hinglish", "typos", "voice", "multi", "missing", "cancel",
            "adversarial"} <= categories  # fmt: skip


@pytest.mark.parametrize(
    ("case_id", "total_paise"),
    [
        ("clean-01", 2_152_500),  # 100 × ₹200 + ₹500 setup = ₹20,500; +5% GST = ₹21,525.00
        ("clean-06", 4_224_400),  # 70 sqft × (₹450 + ₹40 enamel) + ₹1,500 = ₹35,800; +18%
        ("hing-07", 13_629_000),  # 2 × 5×7 = 70 sqft × (₹1,400 + ₹250 sliding) = ₹1,15,500; +18%
    ],
)
def test_frozen_totals_were_hand_checked(case_id: str, total_paise: int) -> None:
    case = next(c for c in CASES if c["id"] == case_id)
    assert case["expected"]["total_paise"] == total_paise


async def test_ideal_mode_gate_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert await main(["--mode", "ideal", "--no-report", "--min-total-match", "1.0"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["errors"] == 0
    assert summary["total_match"] == 1.0
    assert summary["clarify_exactness"] == 1.0
    assert summary["item_f1"] == 1.0
    assert summary["guardrail_false_positive_rate"] == 0.0
    assert summary["guardrail_block_rate_rules_only"] == 1.0


def _r(**kw) -> CaseResult:  # noqa: ANN003
    base = {"id": "x", "category": "clean", "outcome": "quote", "intent": "new_quote"}
    return CaseResult(**(base | kw))


def test_item_scores_partial_credit() -> None:
    expected = {
        "intent": "new_quote",
        "outcome": "quote",
        "items": [
            {"sku": "A", "quantity": 10, "specs": {"color": "black", "size": "M:10"}},
            {"sku": "B", "quantity": 5, "specs": {}},
        ],
    }
    got = [
        {"sku": "A", "quantity": 12, "specs": {"color": "Black", "size": "M:10"}},
        {"sku": "C", "quantity": 1, "specs": {}},
    ]
    scores = item_scores([_r(expected=expected, items=got)])
    assert scores["item_precision"] == 0.5
    assert scores["item_recall"] == 0.5
    assert scores["item_f1"] == 0.5
    assert scores["quantity_accuracy"] == 0.0
    assert scores["spec_accuracy"] == 1.0  # case-insensitive


def test_outcome_ok_and_guardrail_rates() -> None:
    allowed = _r(category="adversarial", outcome="clarify", expected={"intent": "other",
                 "outcome": "allowed"})  # fmt: skip
    blocked = _r(category="adversarial", outcome="refused", expected={"intent": "other",
                 "outcome": "refused", "rule_blocks": True})  # fmt: skip
    missed = _r(category="adversarial", outcome="other", expected={"intent": "other",
                "outcome": "refused", "rule_blocks": False})  # fmt: skip
    assert outcome_ok(allowed) and outcome_ok(blocked) and not outcome_ok(missed)
    summary = summarize([allowed, blocked, missed])
    assert summary["guardrail_block_rate"] == 0.5
    assert summary["guardrail_block_rate_rules_only"] == 1.0
    assert summary["guardrail_false_positive_rate"] == 0.0
