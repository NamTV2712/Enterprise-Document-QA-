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
    CONTEXT_STRATEGY_SELECTIVE_V6,
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.fact_context import select_fact_context_v2
from src.generation.comparative_answerability import (
    assess_comparative_answerability,
)


BASELINE_RESULTS = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
ARTIFACT_PATH = Path(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json"
)
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
    CONTEXT_STRATEGY_SELECTIVE_V6,
    CONTEXT_STRATEGY_SELECTIVE_V7,
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
ENUMERATION_QUESTIONS = {
    case.question
    for case in TEST_SET
    if case.priority <= 2 and case.category == "enumeration"
}
ANSWERABILITY_QUESTIONS = {
    case.question
    for case in TEST_SET
    if case.priority <= 2 and case.category == "comparative"
}
FACT_V2_QUESTIONS = {
    case.question
    for case in TEST_SET
    if case.priority <= 2 and case.category == "fact_lookup"
}


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
    has_unified_metadata = any(
        isinstance(row, dict)
        and (
            "enumeration_applicable" in row
            or "period_value_applicable" in row
        )
        for row in rows.values()
    )
    has_answerability_metadata = any(
        isinstance(row, dict) and "answerability_applicable" in row
        for row in rows.values()
    )
    valid_rows = True
    correction_limits_passed = True
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
        if has_unified_metadata:
            expected_period = question == AWS_QUESTION
            expected_enumeration = question in ENUMERATION_QUESTIONS
            expected_stability = row.get("stability_applicable") is True
            if (
                row.get("period_value_applicable") is not expected_period
                or row.get("enumeration_applicable") is not expected_enumeration
            ):
                valid_rows = False
            if has_answerability_metadata:
                expected_answerability = question in ANSWERABILITY_QUESTIONS
                if row.get("answerability_applicable") is not expected_answerability:
                    valid_rows = False
                if (
                    row.get("answerability_retry_required") is True
                    and not (accepted and final_passed and final_grounding_passed)
                ):
                    valid_rows = False
            if expected_stability and (
                row.get("final_stability_passed", True) is not True
                or row.get("final_stability_missing_facts", []) != []
            ):
                valid_rows = False
            if row.get("correction_attempted") is True and not (
                accepted and final_passed and final_grounding_passed
            ):
                valid_rows = False
        if attempted and not accepted:
            correction_limits_passed = False
        # Safe out-of-corpus fallbacks intentionally have no grounded answer;
        # final grounding is required only for a scoped completion contract or
        # for an answer that attempted a correction. The independent answer
        # integrity gate still audits every non-fallback answer.
        grounding_required = (
            not has_unified_metadata
            or row.get("applicable") is True
            or attempted
        )
        if not final_passed or (
            grounding_required and not final_grounding_passed
        ) or not correction_limits_passed:
            valid_rows = False
    correction_count = sum(
        rows[question].get("correction_attempted") is True
        for question in expected_questions
        if isinstance(rows.get(question), dict)
    )
    max_one_correction = (
        all(
            isinstance(rows.get(question), dict)
            and isinstance(rows[question].get("correction_attempts", 0), int)
            and not isinstance(rows[question].get("correction_attempts"), bool)
            and rows[question].get("correction_attempts", 0) <= 1
            for question in expected_questions
        )
        if has_unified_metadata
        else correction_count <= 1
    )
    expected_applicable_questions = {
        question
        for question in expected_questions
        if question == AWS_QUESTION
        or question in ENUMERATION_QUESTIONS
        or (
            isinstance(rows.get(question), dict)
            and rows[question].get("stability_applicable") is True
        )
    }
    if has_answerability_metadata:
        expected_applicable_questions.update(ANSWERABILITY_QUESTIONS)
    passed = (
        complete
        and (
            set(applicable_questions) == {AWS_QUESTION}
            if not has_unified_metadata
            else set(applicable_questions)
            == expected_applicable_questions
        )
        and valid_rows
        and max_one_correction
    )
    return passed, {
        "metadata_complete": complete,
        "applicable_questions": applicable_questions,
        "unified_metadata": has_unified_metadata,
        "answerability_metadata": has_answerability_metadata,
        "rows_valid": valid_rows,
        "final_grounding_required": True,
        "final_grounding_scope": "applicable_answers_only",
        "correction_count": correction_count,
        "max_one_correction": max_one_correction,
    }


def _target_gate(
    candidate_by_question: dict[str, dict[str, Any]],
    completion_rows: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, dict[str, Any]]:
    apple = candidate_by_question.get(APPLE_QUESTION, {})
    aws = candidate_by_question.get(AWS_QUESTION, {})
    cloud = candidate_by_question.get(CLOUD_DEPENDENCY_QUESTION, {})
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
    cloud_completion = (completion_rows or {}).get(CLOUD_DEPENDENCY_QUESTION) or {}
    # Old candidate fixtures predate the answerability guard. Keep their
    # historical target contract intact; new candidates opt into this gate by
    # persisting the unified answerability metadata.
    answerability_enabled = "answerability_applicable" in cloud_completion
    cloud_answer = (cloud.get("answer") or "").casefold()
    cloud_passed = (
        not answerability_enabled
        or (
            cloud_completion.get("answerability_applicable") is True
            and cloud_completion.get("answerability_evidence_sufficient") is True
            and cloud_completion.get("final_passed") is True
            and cloud_completion.get("final_grounding_passed") is True
            and "could not find sufficient information" not in cloud_answer
            and "cloud" in cloud_answer
            and "services" in cloud_answer
            and _score(cloud, "faithfulness") == 1.0
            and _score(cloud, "answer_relevancy") >= 0.95
        )
    )
    return apple_passed and aws_passed and cloud_passed, {
        "apple_approach": apple_passed,
        "aws_period_value_pairs": aws_passed,
        "cloud_dependency_answerability": cloud_passed,
    }


CLOUD_DEPENDENCY_QUESTION = (
    "Which company depends more on cloud/subscription revenue, Microsoft or Apple?"
)


def _answerability_gate(
    candidate_by_question: dict[str, dict[str, Any]],
    artifact_by_question: dict[str, dict[str, Any]],
    test_by_question: dict[str, Any],
    candidate_strategy: str,
    completion_rows: dict[str, dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    """Recompute the comparative answerability contract provider-free."""
    if not any(
        isinstance(row, dict) and "answerability_applicable" in row
        for row in completion_rows.values()
    ):
        return True, {"applicable": False, "reason": "legacy candidate metadata"}

    rows: dict[str, dict[str, Any]] = {}
    for question in sorted(ANSWERABILITY_QUESTIONS):
        artifact_case = artifact_by_question[question]
        test_case = test_by_question[question]
        context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=candidate_strategy,
        )
        candidate_case = candidate_by_question.get(question, {})
        completion = completion_rows.get(question) or {}
        answer = candidate_case.get("answer") or ""
        assessment = assess_comparative_answerability(question, context, answer)
        metadata_matches = (
            completion.get("answerability_applicable") is assessment.applicable
            and completion.get("answerability_evidence_sufficient")
            is assessment.evidence_sufficient
            and tuple(completion.get("answerability_expected_tickers") or ())
            == assessment.expected_tickers
            and tuple(completion.get("answerability_missing_tickers") or ())
            == assessment.missing_tickers
        )
        safe_final = not (
            assessment.evidence_sufficient and assessment.draft_is_fallback
        )
        rows[question] = {
            "metadata_matches": metadata_matches,
            "evidence_sufficient": assessment.evidence_sufficient,
            "final_fallback": assessment.draft_is_fallback,
            "safe_final": safe_final,
            "retry_required_recorded": completion.get(
                "answerability_retry_required"
            ),
            "expected_tickers": list(assessment.expected_tickers),
            "evidenced_tickers": list(assessment.evidenced_tickers),
            "missing_tickers": list(assessment.missing_tickers),
        }
    passed = all(
        row["metadata_matches"] and row["safe_final"]
        for row in rows.values()
    )
    return passed, {
        "applicable": True,
        "strategy": candidate_strategy,
        "case_count": len(rows),
        "cases": rows,
    }


def _fact_v2_gate(
    candidate_by_question: dict[str, dict[str, Any]],
    artifact_by_question: dict[str, dict[str, Any]],
    test_by_question: dict[str, Any],
    candidate_strategy: str,
) -> tuple[bool, dict[str, Any]]:
    """Audit the additional V2 fact-context contract for a V7 candidate."""
    if candidate_strategy != CONTEXT_STRATEGY_SELECTIVE_V7:
        return True, {"applicable": False, "reason": "not a V7 candidate"}

    fact_rows: dict[str, dict[str, Any]] = {}
    selected_fact_questions = FACT_V2_QUESTIONS & set(artifact_by_question)
    for question in sorted(selected_fact_questions):
        artifact_case = artifact_by_question[question]
        test_case = test_by_question[question]
        selection = select_fact_context_v2(artifact_case)
        v7_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        candidate_case = candidate_by_question.get(question, {})
        scores = candidate_case.get("scores") or {}
        fact_rows[question] = {
            "selector_safe": selection.safe,
            "selector_tier": selection.tier,
            "selector_one_source": len(parse_evidence_context(v7_context)) == 1,
            "faithfulness_exact_one": scores.get("faithfulness") == 1.0,
            "answer_relevancy_floor": (
                isinstance(scores.get("answer_relevancy"), (int, float))
                and scores["answer_relevancy"] >= 0.95
            ),
            "context_precision_target": (
                isinstance(scores.get("context_precision"), (int, float))
                and scores["context_precision"] >= 0.90
            ),
            "scores": scores,
        }

    non_fact_contexts_unchanged = True
    non_fact_rows: dict[str, bool] = {}
    for question in sorted(set(artifact_by_question) - FACT_V2_QUESTIONS):
        artifact_case = artifact_by_question[question]
        test_case = test_by_question[question]
        v5_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
        )
        v7_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        unchanged = v5_context == v7_context
        non_fact_rows[question] = unchanged
        non_fact_contexts_unchanged = non_fact_contexts_unchanged and unchanged

    fact_passed = all(
        row["selector_safe"]
        and row["selector_one_source"]
        and row["faithfulness_exact_one"]
        and row["answer_relevancy_floor"]
        and row["context_precision_target"]
        for row in fact_rows.values()
    ) and len(fact_rows) == len(FACT_V2_QUESTIONS)
    aggregate_cp = [
        float(row["scores"]["context_precision"])
        for row in fact_rows.values()
        if isinstance(row["scores"].get("context_precision"), (int, float))
    ]
    aggregate_cp_value = (
        round(sum(aggregate_cp) / len(aggregate_cp), 4)
        if len(aggregate_cp) == len(fact_rows) and aggregate_cp
        else None
    )
    passed = (
        fact_passed
        and aggregate_cp_value is not None
        and aggregate_cp_value >= 0.90
        and non_fact_contexts_unchanged
    )
    return passed, {
        "applicable": True,
        "fact_case_count": len(fact_rows),
        "fact_cases": fact_rows,
        "fact_context_precision_average": aggregate_cp_value,
        "non_fact_contexts_unchanged": non_fact_contexts_unchanged,
        "non_fact_context_rows": non_fact_rows,
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


def _expected_admission_binding(
    candidate_path: Path,
    baseline_path: Path,
    candidate: dict[str, Any],
    current_binding: str,
) -> str:
    """Select the binding expected by a candidate or official self-check."""
    if candidate_path.resolve() == baseline_path.resolve():
        recorded_binding = candidate.get("binding")
        if candidate.get("official") is True and isinstance(recorded_binding, str):
            return recorded_binding
    return current_binding


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

    # The protected official is a historical, content-addressed benchmark.
    # Its recorded generation binding must remain auditable after a later
    # completion-policy fingerprint changes. Experimental candidates still
    # have to match the current binding computed from the frozen artifact.
    expected_binding = _expected_admission_binding(
        candidate_path,
        baseline_path,
        candidate,
        upstream.binding,
    )

    structural = _structural_gates(
        candidate,
        expected,
        expected_binding,
        candidate_strategy,
    )
    structural["supported_strategy"] = candidate_strategy in SUPPORTED_CANDIDATE_STRATEGIES
    baseline_metrics = _baseline_metrics(baseline)
    metric_thresholds = _metric_thresholds(baseline_metrics)
    metric_gates = _aggregate_metric_gates(candidate, metric_thresholds)
    completion_passed, completion_detail = _completion_gate(candidate, expected)
    completion_rows = candidate.get("period_value_corrections") or {}
    answerability_passed, answerability_detail = _answerability_gate(
        candidate_by_question,
        artifact_by_question,
        test_by_question,
        candidate_strategy,
        completion_rows,
    )
    fact_v2_passed, fact_v2_detail = _fact_v2_gate(
        candidate_by_question,
        artifact_by_question,
        test_by_question,
        candidate_strategy,
    )

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
    target_passed, target_detail = _target_gate(
        candidate_by_question, completion_rows
    )

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
        "answerability_contract": answerability_passed,
        "fact_v2_contract": fact_v2_passed,
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
        "answerability": answerability_detail,
        "fact_v2": fact_v2_detail,
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
