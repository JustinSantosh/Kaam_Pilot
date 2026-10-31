"""Offline eval runner (Phase 12, D-017).

Modes:
  ideal   use each case's labelled ideal LLM output. No network. Checks the deterministic pipeline
          (guardrail rules, validation, pricing) against the frozen expectations. Runs in CI.
  live    call the configured LLM (KP_LLM_MODEL + key) for risk, intent and extraction.
          Add --record to save the raw LLM outputs for replay.
  replay  re-score saved LLM outputs from evals/recordings/<name>.json without calling the LLM.

    python -m evals.run_evals --mode ideal --min-total-match 1.0
    python -m evals.run_evals --mode live --record
    python -m evals.run_evals --mode replay --recording google_genai_gemini-3.5-flash-lite
"""

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.schemas.extraction import Extraction, IntentResult, RiskResult
from app.services import guardrail
from app.services.catalog import load_catalog
from app.services.pricing import price_quote
from app.services.states import state_code
from app.services.validator import validate
from evals.metrics import CaseResult, summarize

HERE = Path(__file__).resolve().parent
DATASET = HERE / "dataset.json"
REPORTS = HERE / "reports"
RECORDINGS = HERE / "recordings"
BUSINESS_STATE = "CG"


class Brain:
    """Where LLM outputs come from in each mode."""

    def __init__(self, mode: str, recording: dict[str, Any] | None = None) -> None:
        self.mode = mode
        self.recording = recording or {}
        self.recorded: dict[str, Any] = {}

    async def risk(self, case: dict) -> RiskResult | None:
        if self.mode == "ideal":
            return None
        if self.mode == "replay":
            raw = self.recording.get(case["id"], {}).get("risk")
            return RiskResult.model_validate(raw) if raw else None
        from app.llm import functions

        result = await functions.classify_risk(case["input"])
        self.recorded.setdefault(case["id"], {})["risk"] = result.model_dump()
        return result

    async def intent(self, case: dict) -> str:
        if self.mode == "ideal":
            return case["ideal"]["intent"]
        if self.mode == "replay":
            return self.recording[case["id"]]["intent"]
        from app.llm import functions

        result: IntentResult = await functions.classify_intent(case["input"])
        self.recorded.setdefault(case["id"], {})["intent"] = result.intent
        return result.intent

    async def extract(self, case: dict, catalog: Any) -> Extraction:
        if self.mode == "ideal":
            return Extraction.model_validate(case["ideal"]["extraction"])
        if self.mode == "replay":
            return Extraction.model_validate(self.recording[case["id"]]["extraction"])
        from app.llm import functions

        result = await functions.extract(case["input"], catalog=catalog)
        self.recorded.setdefault(case["id"], {})["extraction"] = result.model_dump(mode="json")
        return result


async def run_case(case: dict, brain: Brain, catalog: Any) -> CaseResult:
    started = time.perf_counter()
    result = CaseResult(
        id=case["id"], category=case["category"], expected=case["expected"], outcome="", intent=""
    )
    try:
        risk = await brain.risk(case)

        async def risk_fn(_: str) -> RiskResult:
            if risk is None:
                raise LookupError("no risk check in this mode")
            return risk

        verdict = await guardrail.check(case["input"], risk_fn if risk else None)
        result.money_flag = guardrail.FLAG_MONEY_OVERRIDE in verdict.flags
        if verdict.flagged:
            result.outcome, result.refused_by = "refused", verdict.source
            return result

        result.intent = await brain.intent(case)
        if result.intent != "new_quote":
            result.outcome = result.intent
            return result

        extraction = await brain.extract(case, catalog)
        checked = validate(extraction, catalog)
        result.items = [{"sku": v.sku, "quantity": v.quantity, "specs": v.specs}
                        for v in checked.items]  # fmt: skip
        result.missing = sorted(
            f"{v.index}:{i.code}:{i.field or ''}" for v in checked.items for i in v.issues
        )
        if not checked.complete:
            result.outcome = "clarify"
            return result
        state = state_code(case["customer_state"]) or state_code(extraction.customer_state)
        priced = price_quote(
            checked.pricing_inputs(), catalog=catalog, business_state=BUSINESS_STATE,
            customer_state=state,
        )  # fmt: skip
        result.outcome, result.total_paise = "quote", priced.totals.total_paise
        return result
    except Exception as exc:  # one bad case shouldn't stop the run
        result.outcome, result.error = "error", f"{type(exc).__name__}: {exc}"
        return result
    finally:
        result.latency_ms = (time.perf_counter() - started) * 1000


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_report(summary: dict, results: list[CaseResult], label: str) -> str:
    rows = [
        ("Outcome accuracy", "outcome_accuracy"),
        ("Intent accuracy", "intent_accuracy"),
        ("Item precision", "item_precision"),
        ("Item recall", "item_recall"),
        ("Item F1", "item_f1"),
        ("Quantity accuracy", "quantity_accuracy"),
        ("Spec accuracy", "spec_accuracy"),
        ("Clarification exactness", "clarify_exactness"),
        ("**End-to-end total match**", "total_match"),
        ("Guardrail block rate", "guardrail_block_rate"),
        ("Guardrail block rate (rule-blockable cases)", "guardrail_block_rate_rules_only"),
        ("Guardrail false-positive rate", "guardrail_false_positive_rate"),
        ("Money-override flag rate", "money_override_flag_rate"),
    ]
    lines = [
        f"# KaamPilot eval report: {label}",
        "",
        f"- Date: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
        f"- Cases: {summary['cases']} · errors: {summary['errors']}",
        f"- Latency p50 / p95: {summary['latency_ms_p50'] or 0:.0f} ms / "
        f"{summary['latency_ms_p95'] or 0:.0f} ms",
        "",
        "| Metric | Value |",
        "|---|---|",
        *[f"| {name} | {_pct(summary[key])} |" for name, key in rows],
        "",
        "## By category",
        "",
        "| Category | Cases | Outcome accuracy |",
        "|---|---|---|",
        *[
            f"| {cat} | {v['cases']} | {_pct(v['outcome_accuracy'])} |"
            for cat, v in summary["by_category"].items()
        ],
        "",
        "## Mismatches",
        "",
    ]
    misses = [
        r for r in results
        if r.error or r.outcome != r.expected["outcome"] and r.expected["outcome"] != "allowed"
        or (r.expected["outcome"] == "quote" and r.total_paise != r.expected.get("total_paise"))
    ]  # fmt: skip
    if not misses:
        lines.append("None.")
    for r in misses[:30]:
        detail = r.error or f"expected {r.expected['outcome']}, got {r.outcome}"
        if r.outcome == "clarify":
            detail += f" (missing: {', '.join(r.missing)})"
        lines.append(f"- `{r.id}` ({r.category}): {detail}")
    return "\n".join(lines) + "\n"


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=["ideal", "live", "replay"], default="ideal")
    parser.add_argument("--record", action="store_true", help="live mode: save LLM outputs")
    parser.add_argument("--recording", help="replay mode: recording name (file stem)")
    parser.add_argument("--min-total-match", type=float, default=None)
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args(argv)

    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    model = get_settings().llm_model or "unset"
    name = re.sub(r"[^A-Za-z0-9.-]+", "_", model)
    recording = None
    if args.mode == "replay":
        stem = args.recording or name
        recording = json.loads((RECORDINGS / f"{stem}.json").read_text(encoding="utf-8"))
        name = stem
    brain = Brain(args.mode, recording)
    catalog = load_catalog()

    results = [await run_case(c, brain, catalog) for c in cases]
    summary = summarize(results)
    label = "ideal (deterministic pipeline)" if args.mode == "ideal" else f"{args.mode} · {name}"

    if args.record and args.mode == "live":
        RECORDINGS.mkdir(exist_ok=True)
        (RECORDINGS / f"{name}.json").write_text(json.dumps(brain.recorded, indent=1), "utf-8")
    if not args.no_report:
        REPORTS.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        path = REPORTS / f"{stamp}-{args.mode}-{name if args.mode != 'ideal' else 'pipeline'}.md"
        path.write_text(render_report(summary, results, label), encoding="utf-8")
        print(f"report: {path.relative_to(HERE.parent)}")

    print(json.dumps({k: v for k, v in summary.items() if k != "by_category"}, indent=1))
    if args.min_total_match is not None and (summary["total_match"] or 0) < args.min_total_match:
        print(f"FAIL: total_match {summary['total_match']} < {args.min_total_match}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
