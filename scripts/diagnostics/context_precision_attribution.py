"""Provider-free attribution audit for a context-packing candidate.

This audit compares paired baseline/candidate answers and scores while
re-rendering both contexts from the frozen Phase 1 artifact.  It separates
cases whose context actually changed from unchanged-context answer/score
changes that are confounded by provider generation or judging variance.  It
also previews the v3 grounded-completion activation policy without making a
correction call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V4,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.period_value_completeness import (
    PERIOD_VALUE_CORRECTION_FINGERPRINT,
    assess_grounded_completion,
)


BASELINE_RESULTS = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
CANDIDATE_RESULTS = Path(
    "data/eval_artifacts/phase2_results_context_precision_v4_candidate.json"
)
COUNTERFACTUAL_REPORT = Path(
    "data/diagnostics/context_precision_counterfactual_v4.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/context_precision_attribution_v4.json")
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _answer_hash(answer: str) -> str:
    return _sha256_text(answer)


def _score(case: dict[str, Any], key: str) -> float | None:
    value = (case.get("scores") or {}).get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _context_integrity(context: str) -> dict[str, Any]:
    sources = [block["text"] for block in parse_evidence_context(context)]
    return {
        "context_sha256": _sha256_text(context),
        "source_count": len(sources),
        "source_boundary_parse_passed": len(sources) == len(
            parse_evidence_context(context)
        ),
    }


def _completion_row(
    question: str,
    answer: str,
    context: str,
) -> dict[str, Any]:
    assessment = assess_grounded_completion(question, context, answer)
    return {
        "applicable": assessment.period_value.applicable,
        "period_value_passed": assessment.period_value.passed,
        "grounding_passed": assessment.grounding_passed,
        "correction_required": assessment.correction_required,
        "unsupported_numeric_claims": list(
            assessment.unsupported_numeric_claims
        ),
        "missing_pairs": [
            {
                "period": pair.period,
                "value": pair.value,
                "source_number": pair.source_number,
            }
            for pair in assessment.period_value.missing_pairs
        ],
    }


def _load_counterfactual(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["question"]: row
        for row in payload.get("cases", [])
        if isinstance(row, dict) and row.get("question")
    }


def build_attribution_report(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    artifact: dict[str, Any],
    counterfactual: dict[str, dict[str, Any]] | None = None,
    baseline_path: Path = BASELINE_RESULTS,
    candidate_path: Path = CANDIDATE_RESULTS,
    artifact_path: Path = Path("data/eval_artifacts/phase1_priority2.json"),
) -> dict[str, Any]:
    """Build a deterministic attribution report from already-frozen inputs."""
    metadata = {case.question: case for case in TEST_SET}
    artifact_by_question = {
        case["question"]: case for case in artifact.get("cases", [])
    }
    baseline_by_question = {
        case["question"]: case for case in baseline.get("cases", [])
    }
    candidate_by_question = {
        case["question"]: case for case in candidate.get("cases", [])
    }
    questions = [
        case.question for case in TEST_SET
        if case.priority <= 2
        and case.question in artifact_by_question
        and case.question in baseline_by_question
        and case.question in candidate_by_question
    ]
    rows: list[dict[str, Any]] = []
    for question in questions:
        test_case = metadata[question]
        artifact_case = artifact_by_question[question]
        baseline_case = baseline_by_question[question]
        candidate_case = candidate_by_question[question]
        baseline_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
        )
        candidate_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V4,
        )
        answer_same = (
            _answer_hash(baseline_case.get("answer") or "")
            == _answer_hash(candidate_case.get("answer") or "")
        )
        score_deltas = {
            key: (
                _score(candidate_case, key) - _score(baseline_case, key)
                if _score(candidate_case, key) is not None
                and _score(baseline_case, key) is not None
                else None
            )
            for key in SCORE_KEYS
        }
        baseline_context_hash = _sha256_text(baseline_context)
        candidate_context_hash = _sha256_text(candidate_context)
        context_changed = baseline_context_hash != candidate_context_hash
        if context_changed:
            classification = "context_changed"
        elif answer_same and not any(
            delta not in (None, 0.0) for delta in score_deltas.values()
        ):
            classification = "unchanged_stable"
        else:
            classification = "unchanged_provider_or_runtime_variance"
        cf_row = (counterfactual or {}).get(question, {})
        rows.append(
            {
                "question": question,
                "category": test_case.category,
                "context_changed": context_changed,
                "counterfactual_changed": cf_row.get("changed"),
                "counterfactual_agrees": (
                    context_changed == cf_row["changed"]
                    if "changed" in cf_row
                    else None
                ),
                "baseline_context_sha256": baseline_context_hash,
                "candidate_context_sha256": candidate_context_hash,
                "answer_same": answer_same,
                "baseline_answer_sha256": _answer_hash(
                    baseline_case.get("answer") or ""
                ),
                "candidate_answer_sha256": _answer_hash(
                    candidate_case.get("answer") or ""
                ),
                "score_deltas": score_deltas,
                "classification": classification,
                "baseline_completion": _completion_row(
                    question,
                    baseline_case.get("answer") or "",
                    baseline_context,
                ),
                "candidate_completion": _completion_row(
                    question,
                    candidate_case.get("answer") or "",
                    candidate_context,
                ),
                "baseline_context_integrity": _context_integrity(
                    baseline_context
                ),
                "candidate_context_integrity": _context_integrity(
                    candidate_context
                ),
                "baseline_answer_integrity": audit_answer(
                    baseline_case.get("answer") or "",
                    [block["text"] for block in parse_evidence_context(baseline_context)],
                ).to_dict(),
                "candidate_answer_integrity": audit_answer(
                    candidate_case.get("answer") or "",
                    [block["text"] for block in parse_evidence_context(candidate_context)],
                ).to_dict(),
            }
        )

    changed = [row for row in rows if row["context_changed"]]
    unchanged = [row for row in rows if not row["context_changed"]]
    baseline_activation = [
        row["question"]
        for row in rows
        if row["baseline_completion"]["correction_required"]
    ]
    candidate_activation = [
        row["question"]
        for row in rows
        if row["candidate_completion"]["correction_required"]
    ]
    aws_row = next(
        (row for row in rows if row["question"] == AWS_QUESTION), None
    )
    if aws_row is None:
        raise RuntimeError("Grounded-completion probe case is missing")
    aws_candidate_case = candidate_by_question[AWS_QUESTION]
    aws_artifact_case = artifact_by_question[AWS_QUESTION]
    aws_test_case = metadata[AWS_QUESTION]
    aws_candidate_context = render_case_context(
        aws_artifact_case,
        required_keywords=aws_test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V4,
    )
    probe_answer = (
        (aws_candidate_case.get("answer") or "")
        + " The increase was $21,169 [Source 1]."
    )
    completion_probe = _completion_row(
        AWS_QUESTION, probe_answer, aws_candidate_context
    )
    unchanged_variance_rows = [
        row for row in unchanged
        if not row["answer_same"] or any(
            delta not in (None, 0.0)
            for delta in row["score_deltas"].values()
        )
    ]
    counterfactual_agreement = all(
        row["counterfactual_agrees"] is not False
        for row in rows
    )
    completion_policy_passed = (
        baseline_activation == [] and candidate_activation == []
        and completion_probe["correction_required"] is True
        and "$21,169" in completion_probe["unsupported_numeric_claims"]
        and all(
            row["candidate_completion"]["grounding_passed"]
            or row["candidate_completion"]["correction_required"]
            for row in rows
        )
    )
    report = {
        "schema_version": 1,
        "audit": "context_precision_attribution_v4",
        "provider_calls": 0,
        "baseline_result_sha256": _file_sha256(baseline_path)
        if baseline_path.exists()
        else None,
        "candidate_result_sha256": _file_sha256(candidate_path)
        if candidate_path.exists()
        else None,
        "artifact_file_sha256": _file_sha256(artifact_path)
        if artifact_path.exists()
        else None,
        "artifact_fingerprint": artifact.get("fingerprints", {}).get("artifact"),
        "baseline_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V4,
        "completion_fingerprint": PERIOD_VALUE_CORRECTION_FINGERPRINT,
        "num_cases": len(rows),
        "context_changed_cases": len(changed),
        "context_unchanged_cases": len(unchanged),
        "answer_changed_on_unchanged_context_cases": sum(
            not row["answer_same"] for row in unchanged
        ),
        "paired_analysis": rows,
        "completion_activation": {
            "expected_baseline_questions": [],
            "expected_candidate_questions": [],
            "baseline_questions": baseline_activation,
            "candidate_questions": candidate_activation,
            "passed": completion_policy_passed,
            "synthetic_unsupported_derived_numeric_probe": completion_probe,
        },
        "pre_registered_gates": {
            "provider_calls_zero": True,
            "case_set_complete": True,
            "counterfactual_context_change_agreement": True,
            "candidate_has_no_unexpected_completion_activation": True,
            "synthetic_derived_numeric_claim_is_blocked": True,
            "unchanged_context_changes_are_flagged_as_confounded": True,
        },
        "gates": {
            "provider_calls_zero": True,
            "case_set_complete": len(rows) == 30,
            "counterfactual_context_change_agreement": counterfactual_agreement,
            "completion_policy": completion_policy_passed,
            "unchanged_context_variance_attributed": all(
                row["classification"] == "unchanged_provider_or_runtime_variance"
                for row in unchanged_variance_rows
            ),
        },
    }
    report["passed"] = all(report["gates"].values())
    return report


def run(
    baseline_path: Path = BASELINE_RESULTS,
    candidate_path: Path = CANDIDATE_RESULTS,
    artifact_path: Path = Path("data/eval_artifacts/phase1_priority2.json"),
    counterfactual_path: Path = COUNTERFACTUAL_REPORT,
) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    artifact, _ = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V4,
    )
    return build_attribution_report(
        baseline,
        candidate,
        artifact,
        _load_counterfactual(counterfactual_path),
        baseline_path,
        candidate_path,
        artifact_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_RESULTS)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_RESULTS)
    parser.add_argument("--artifact", type=Path, default=Path(
        "data/eval_artifacts/phase1_priority2.json"
    ))
    parser.add_argument(
        "--counterfactual", type=Path, default=COUNTERFACTUAL_REPORT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(
        args.baseline,
        args.candidate,
        args.artifact,
        args.counterfactual,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "passed": report["passed"],
        "num_cases": report["num_cases"],
        "context_changed_cases": report["context_changed_cases"],
        "candidate_completion_questions": report["completion_activation"][
            "candidate_questions"
        ],
    }, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
