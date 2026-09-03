"""Audit the final Answer Scope sentinel pair without provider calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.diagnostics import answer_scope_v14_reproducibility as base
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.revenue_intent_contract import (
    MICROSOFT_MAIN_REVENUE_QUESTION,
    REVENUE_INTENT_CONTRACT_FINGERPRINT,
    audit_revenue_intent_scope,
)
from src.evaluation.test_set import TEST_SET
from src.generation.risk_answer_shape import RISK_ANSWER_SHAPE_FINGERPRINT


ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
DEFAULT_R1 = Path(
    "data/eval_artifacts/answer_scope_closure_v1_sentinel_summary_r1.json"
)
DEFAULT_R2 = Path(
    "data/eval_artifacts/answer_scope_closure_v1_sentinel_summary_r2.json"
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/answer_scope_closure_v1_reproducibility.json"
)


def _answer(report: dict[str, Any]) -> str:
    for case in report.get("cases", []):
        if case.get("question") == MICROSOFT_MAIN_REVENUE_QUESTION:
            return str(case.get("answer") or "")
    return ""


def _revenue_context() -> str:
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    artifact_case = next(
        case
        for case in artifact["cases"]
        if case["question"] == MICROSOFT_MAIN_REVENUE_QUESTION
    )
    test_case = next(
        case
        for case in TEST_SET
        if case.question == MICROSOFT_MAIN_REVENUE_QUESTION
    )
    return render_case_context(
        artifact_case,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
    )


def build_report(
    first: dict[str, Any],
    second: dict[str, Any],
    first_path: Path | None = None,
    second_path: Path | None = None,
) -> dict[str, Any]:
    report = base.build_report(first, second, first_path, second_path)
    context = _revenue_context()
    first_scope = audit_revenue_intent_scope(
        MICROSOFT_MAIN_REVENUE_QUESTION, context, _answer(first)
    )
    second_scope = audit_revenue_intent_scope(
        MICROSOFT_MAIN_REVENUE_QUESTION, context, _answer(second)
    )
    gates = dict(report.get("gates") or {})
    gates.update(
        {
            "revenue_intent_contract_fingerprint": (
                first.get("revenue_intent_contract_fingerprint")
                == REVENUE_INTENT_CONTRACT_FINGERPRINT
                and second.get("revenue_intent_contract_fingerprint")
                == REVENUE_INTENT_CONTRACT_FINGERPRINT
            ),
            "same_revenue_intent_contract": (
                first_scope.get("passed") is True
                and second_scope.get("passed") is True
            ),
            "same_revenue_answer_scope": (
                _answer(first) == _answer(second) and bool(_answer(first))
            ),
            "same_risk_answer_shape_fingerprint": (
                first.get("risk_answer_shape_fingerprint")
                == RISK_ANSWER_SHAPE_FINGERPRINT
                and second.get("risk_answer_shape_fingerprint")
                == RISK_ANSWER_SHAPE_FINGERPRINT
            ),
        }
    )
    report.update(
        {
            "audit": "answer_scope_reproducibility_closure_v1",
            "revenue_intent_contract_fingerprint": REVENUE_INTENT_CONTRACT_FINGERPRINT,
            "revenue_scope_r1": first_scope,
            "revenue_scope_r2": second_scope,
            "gates": gates,
            "passed": all(gates.values()),
        }
    )
    return report


def run(
    first_path: Path = DEFAULT_R1,
    second_path: Path = DEFAULT_R2,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    first = json.loads(first_path.read_text(encoding="utf-8"))
    second = json.loads(second_path.read_text(encoding="utf-8"))
    report = build_report(first, second, first_path, second_path)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--r2", type=Path, default=DEFAULT_R2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(args.r1, args.r2, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
