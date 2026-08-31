"""Provider-free admission audit for a Phase 2 candidate result.

The audit compares a complete candidate against the recorded official
``selective_packed_v2`` result. It never changes the official result and it
never makes provider calls. A candidate is admitted only when structural,
grounding, completion-policy, targeted semantic, and aggregate non-regression
gates all pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    CONTEXT_STRATEGY_COMPARATIVE_V4,
    CONTEXT_STRATEGY_COMPARATIVE_V5,
    CONTEXT_STRATEGY_COMPARATIVE_V6,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    CONTEXT_STRATEGY_ROUTE_AWARE_V3,
    CONTEXT_STRATEGY_ROUTE_AWARE_V4,
    CONTEXT_STRATEGY_SELECTIVE,
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V4,
    CONTEXT_STRATEGY_SELECTIVE_V5,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET


BASELINE_RESULTS = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
DEFAULT_OUTPUT = Path("data/diagnostics/phase2_admission.json")

ADMISSION_METRIC_KEYS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "overall_judge_average",
)
FAITHFULNESS_TOLERANCE = 0.01
MAX_NON_TARGET_SEMANTIC_DROP = 0.10

SUPPORTED_CANDIDATE_STRATEGIES = {
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    CONTEXT_STRATEGY_ROUTE_AWARE_V3,
    CONTEXT_STRATEGY_ROUTE_AWARE_V4,
    CONTEXT_STRATEGY_SELECTIVE,
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V4,
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    CONTEXT_STRATEGY_COMPARATIVE_V4,
    CONTEXT_STRATEGY_COMPARATIVE_V5,
    CONTEXT_STRATEGY_COMPARATIVE_V6,
}

APPLE_QUESTION = "Compare Apple and Microsoft's approach to cloud/services revenue."
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
AWS_VALUES = ("107,556", "128,725")
AWS_PERIODS = ("2024", "2025")


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _metric(candidate: dict[str, Any], key: str) -> float | None:
    value = candidate.get("metrics", {}).get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _baseline_metrics(baseline: dict[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key in ADMISSION_METRIC_KEYS:
        value = _metric(baseline, key)
        if value is None:
            raise RuntimeError(f"official baseline is missing numeric metric {key!r}")
        metrics[key] = value
    return metrics


def _metric_thresholds(
    baseline_metrics: dict[str, float],
) -> dict[str, float]:
    """Derive candidate floors from the protected official at audit time."""
    return {
        "faithfulness": round(
            baseline_metrics["faithfulness"] - FAITHFULNESS_TOLERANCE, 4
        ),
        "answer_relevancy": baseline_metrics["answer_relevancy"],
        "context_precision": baseline_metrics["context_precision"],
        "overall_judge_average": baseline_metrics["overall_judge_average"],
    }


def _score(candidate_case: dict[str, Any], key: str) -> float | None:
    value = candidate_case.get("scores", {}).get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _case_integrity(
    candidate_case: dict[str, Any],
    artifact_case: dict[str, Any],
    test_case: Any,
    context_strategy: str = CONTEXT_STRATEGY_SELECTIVE_V2,
) -> dict[str, Any]:
    context = render_case_context(
        artifact_case,
        required_keywords=test_case.required_keywords,
        strategy=context_strategy,
    )
    source_texts = [
        block["text"] for block in parse_evidence_context(context)
    ]
    answer_audit = audit_answer(candidate_case.get("answer") or "", source_texts)
    answerable_fallback = (
        answer_audit.fallback_answer and not test_case.expects_fallback
    )
    return {
        "question": test_case.question,
        "context_sha256": _sha256_text(context),
        "fallback_answer": answer_audit.fallback_answer,
        "answerable_fallback": answerable_fallback,
        "uncited_non_fallback": (
            answer_audit.uncited_answer and not answer_audit.fallback_answer
        ),
        "legacy_line_citation": answer_audit.malformed_line_citations > 0,
        "out_of_range_citation": bool(answer_audit.out_of_range_citations),
        "unsupported_numeric_claim": bool(
            answer_audit.unsupported_numeric_claims
        ),
        "audit": answer_audit.to_dict(),
    }


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _completion_gate(
    candidate: dict[str, Any], expected_questions: list[str]
) -> tuple[bool, dict[str, Any]]:
    rows = candidate.get("period_value_corrections")
    rows = rows if isinstance(rows, dict) else {}
    complete = set(rows) == set(expected_questions)
    applicable_questions = [
        question for question in expected_questions
        if isinstance(rows.get(question), dict)
        and rows[question].get("applicable") is True
    ]
    valid_rows = True
    for question in expected_questions:
        row = rows.get(question)
        if not isinstance(row, dict):
            valid_rows = False
            continue
        attempted = row.get("correction_attempted") is True
        accepted = row.get("correction_accepted") is True
        final_passed = row.get("final_passed") is True
        # Older candidate metadata predates the v3 grounding field; retain
        # compatibility for those frozen records while requiring the field
        # whenever a newer run provides it.
        final_grounding_passed = row.get("final_grounding_passed", True) is True
        if (
            not final_passed
            or not final_grounding_passed
            or (attempted and not accepted)
        ):
            valid_rows = False
    passed = (
        complete
        and applicable_questions == [AWS_QUESTION]
        and valid_rows
        and sum(
            rows[question].get("correction_attempted") is True
            for question in expected_questions
            if isinstance(rows.get(question), dict)
        ) <= 1
    )
    return passed, {
        "metadata_complete": complete,
        "applicable_questions": applicable_questions,
        "rows_valid": valid_rows,
        "final_grounding_required": True,
        "max_one_correction": (
            sum(
                rows[question].get("correction_attempted") is True
                for question in expected_questions
                if isinstance(rows.get(question), dict)
            ) <= 1
        ),
    }


def _target_gate(
    candidate_by_question: dict[str, dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    apple = candidate_by_question.get(APPLE_QUESTION, {})
    aws = candidate_by_question.get(AWS_QUESTION, {})
    apple_answer = (apple.get("answer") or "").casefold()
    aws_answer = aws.get("answer") or ""
    apple_passed = (
        "services" in apple_answer
        and "azure" in apple_answer
        and any(
            term in apple_answer
            for term in ("cloud services", "cloud storage", "app store", "advertising")
        )
        and _score(apple, "faithfulness") is not None
        and _score(apple, "faithfulness") >= 0.90
        and _score(apple, "answer_relevancy") is not None
        and _score(apple, "answer_relevancy") >= 0.90
    )
    aws_passed = (
        all(value in aws_answer for value in AWS_VALUES)
        and all(period in aws_answer for period in AWS_PERIODS)
        and _score(aws, "faithfulness") is not None
        and _score(aws, "faithfulness") >= 0.90
        and _score(aws, "answer_relevancy") is not None
        and _score(aws, "answer_relevancy") >= 0.90
    )
    return apple_passed and aws_passed, {
        "apple_approach": apple_passed,
        "aws_period_value_pairs": aws_passed,
    }


def _aggregate_metric_gates(
    candidate: dict[str, Any], thresholds: dict[str, float]
) -> dict[str, bool]:
    values = {
        key: _metric(candidate, key)
        for key in ADMISSION_METRIC_KEYS
    }
    return {
        "faithfulness": (
            values["faithfulness"] is not None
            and values["faithfulness"] >= thresholds["faithfulness"]
        ),
        "answer_relevancy": (
            values["answer_relevancy"] is not None
            and values["answer_relevancy"] >= thresholds["answer_relevancy"]
        ),
        "context_precision": (
            values["context_precision"] is not None
            and values["context_precision"] >= thresholds["context_precision"]
        ),
        "overall": (
            values["overall_judge_average"] is not None
            and values["overall_judge_average"]
            >= thresholds["overall_judge_average"]
        ),
    }


def _structural_gates(
    candidate: dict[str, Any],
    expected_questions: list[str],
    expected_binding: str,
    expected_strategy: str = CONTEXT_STRATEGY_SELECTIVE_V2,
) -> dict[str, bool]:
    cases = candidate.get("cases") or []
    observed_questions = [case.get("question") for case in cases]
    return {
        "candidate_complete": (
            (
                candidate.get("provider_complete") is True
                or candidate.get("official") is True
            )
            and candidate.get("stopped_reason") is None
            and candidate.get("num_selected") == len(expected_questions)
            and candidate.get("num_generation_ok") == len(expected_questions)
            and candidate.get("num_judged_ok") == len(expected_questions)
        ),
        "case_set_exact": (
            len(observed_questions) == len(expected_questions)
            and set(observed_questions) == set(expected_questions)
        ),
        "single_binding": candidate.get("binding") == expected_binding,
        "artifact_bound": (
            candidate.get("bound_artifact_fingerprint")
            == EXPECTED_ARTIFACT_FINGERPRINT
        ),
        "model_bound": (
            candidate.get("model") == EVAL_MODEL
            and candidate.get("judge_model") == EVAL_MODEL
        ),
        "strategy_bound": (
            candidate.get("context_strategy") == expected_strategy
        ),
        "all_case_statuses_ok": all(
            case.get("generation_status") == "OK"
            and case.get("judge_status") == "OK"
            for case in cases
        ),
    }


def run(
    candidate_path: Path,
    baseline_path: Path = BASELINE_RESULTS,
    artifact_path: Path = ARTIFACT_PATH,
) -> dict[str, Any]:
    """Build a deterministic admission report for one candidate result."""
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate_strategy = candidate.get("context_strategy")
    if not isinstance(candidate_strategy, str) or not candidate_strategy:
        candidate_strategy = CONTEXT_STRATEGY_SELECTIVE_V2
    artifact, upstream = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        candidate_strategy,
    )
    expected = [case.question for case in TEST_SET if case.priority <= 2]
    test_by_question = {case.question: case for case in TEST_SET}
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}
    candidate_by_question = {
        case.get("question"): case for case in candidate.get("cases", [])
    }

    structural = _structural_gates(
        candidate,
        expected,
        upstream.binding,
        candidate_strategy,
    )
    structural["supported_strategy"] = candidate_strategy in SUPPORTED_CANDIDATE_STRATEGIES
    baseline_metrics = _baseline_metrics(baseline)
    metric_thresholds = _metric_thresholds(baseline_metrics)
    metric_gates = _aggregate_metric_gates(candidate, metric_thresholds)
    completion_passed, completion_detail = _completion_gate(candidate, expected)

    integrity_rows = [
        _case_integrity(
            candidate_by_question[question],
            artifact_by_question[question],
            test_by_question[question],
            candidate_strategy,
        )
        for question in expected
        if question in candidate_by_question and question in artifact_by_question
    ]
    integrity = {
        "all_cases_audited": len(integrity_rows) == len(expected),
        "uncited_non_fallback": sum(
            row["uncited_non_fallback"] for row in integrity_rows
        ) == 0,
        "legacy_line_citations": sum(
            row["legacy_line_citation"] for row in integrity_rows
        ) == 0,
        "out_of_range_citations": sum(
            row["out_of_range_citation"] for row in integrity_rows
        ) == 0,
        "unsupported_numeric_claims": sum(
            row["unsupported_numeric_claim"] for row in integrity_rows
        ) == 0,
        "answerable_fallbacks": sum(
            row["answerable_fallback"] for row in integrity_rows
        ) == 0,
    }
    target_passed, target_detail = _target_gate(candidate_by_question)

    baseline_cases = {
        case.get("question"): case for case in baseline.get("cases", [])
    }
    non_target_regressions: list[dict[str, Any]] = []
    for question in expected:
        if question in {APPLE_QUESTION, AWS_QUESTION}:
            continue
        before = baseline_cases.get(question, {})
        after = candidate_by_question.get(question, {})
        for metric in ("faithfulness", "answer_relevancy"):
            old = _score(before, metric)
            new = _score(after, metric)
            if old is not None and new is not None and new < old - MAX_NON_TARGET_SEMANTIC_DROP:
                non_target_regressions.append({
                    "question": question,
                    "metric": metric,
                    "baseline": old,
                    "candidate": new,
                })
    regression = {
        "no_non_target_semantic_regression": not non_target_regressions,
        "cases": non_target_regressions,
    }

    gates = {
        **{f"structure_{key}": value for key, value in structural.items()},
        **{f"aggregate_{key}": value for key, value in metric_gates.items()},
        **{f"integrity_{key}": value for key, value in integrity.items()},
        "completion_policy": completion_passed,
        "target_cases": target_passed,
        "non_target_regression": regression["no_non_target_semantic_regression"],
    }
    admitted = all(gates.values())
    return {
        "schema_version": 2,
        "admission": admitted,
        "candidate_path": str(candidate_path),
        "candidate_sha256": _file_sha256(candidate_path),
        "baseline_path": str(baseline_path),
        "baseline_sha256": _file_sha256(baseline_path),
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "binding": upstream.binding,
        "context_strategy": candidate_strategy,
        "expected_cases": len(expected),
        "baseline_metrics": baseline_metrics,
        "aggregate_metric_thresholds": metric_thresholds,
        "candidate_metrics": {
            key: _metric(candidate, key) for key in ADMISSION_METRIC_KEYS
        },
        "structural": structural,
        "aggregate_metric_gates": metric_gates,
        "completion": completion_detail,
        "target": target_detail,
        "integrity": integrity,
        "integrity_cases": integrity_rows,
        "regression": regression,
        "gates": gates,
        "passed": admitted,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=BASELINE_RESULTS)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = run(args.candidate, args.baseline, args.artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
