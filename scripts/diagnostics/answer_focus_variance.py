"""Audit answer-focus drift and risk-enumeration granularity offline.

This diagnostic compares the protected official result, the V7 candidate, and
the two answer-stability sentinels.  It re-renders contexts from the frozen
Phase 1 artifact and uses only evidence-derived completion metadata.  It does
not consume ground truth, required keywords, or provider calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.enumeration_completeness import (
    _bullet_count,
    _bullet_item_matches,
    _unclassified_bullet_indexes,
    assess_enumeration_completeness,
)


OFFICIAL_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
CANDIDATE_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_answer_stability_v7_candidate.json"
)
SENTINEL_R1_PATH = Path(
    "data/eval_artifacts/answer_stability_v1_sentinel_summary_r1.json"
)
SENTINEL_R2_PATH = Path(
    "data/eval_artifacts/answer_stability_v1_sentinel_summary_r2.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/answer_focus_variance_v1.json")
EXPECTED_OFFICIAL_SHA256 = (
    "sha256:a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
EXPECTED_CANDIDATE_SHA256 = (
    "sha256:c9fca766a0aff6ae3ebdf49d795178614e74e18f6d6696b07bd6917aa2132cb9"
)
APPLE_QUALITY_QUESTION = "What quality and manufacturing risks does Apple mention?"
MICROSOFT_RISK_QUESTION = "What are all the major risk factors Microsoft discloses?"
EXPECTED_REGRESSIONS = (APPLE_QUALITY_QUESTION, MICROSOFT_RISK_QUESTION)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _text_sha256(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _score(case: dict[str, Any], key: str) -> float | None:
    value = (case.get("scores") or {}).get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _case_map(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        case["question"]: case
        for case in document.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("question"), str)
    }


def _context_summary(context: str) -> dict[str, Any]:
    blocks = parse_evidence_context(context)
    return {
        "context_sha256": _text_sha256(context),
        "source_count": len(blocks),
        "source_boundary_parse_passed": bool(blocks)
        and all(
            isinstance(block.get("text"), str) and block.get("text")
            for block in blocks
        ),
    }


def _risk_shape(
    question: str,
    answer: str,
    context: str,
) -> dict[str, Any]:
    assessment = assess_enumeration_completeness(question, context, answer)
    lines = answer.splitlines()
    unclassified = _unclassified_bullet_indexes(answer, assessment)
    matches = _bullet_item_matches(answer, assessment)
    return {
        "applicable": assessment.applicable,
        "kind": assessment.kind,
        "evidence_items": [
            {
                "label": item.label,
                "source_number": item.source_number,
                "aliases": list(item.aliases),
            }
            for item in assessment.evidence_items
        ],
        "covered_items": [item.label for item in assessment.covered_items],
        "missing_items": [item.label for item in assessment.missing_items],
        "passed": assessment.passed,
        "overdetailed": assessment.overdetailed,
        "bullet_count": _bullet_count(answer),
        "matched_bullet_count": len(matches),
        "unclassified_bullets": [lines[index] for index in unclassified],
    }


def _render(
    artifact_case: dict[str, Any],
    test_case: Any,
    strategy: str,
) -> str:
    return render_case_context(
        artifact_case,
        required_keywords=test_case.required_keywords,
        strategy=strategy,
    )


def build_report(
    official: dict[str, Any],
    candidate: dict[str, Any],
    sentinel_r1: dict[str, Any],
    sentinel_r2: dict[str, Any],
    artifact: dict[str, Any],
    *,
    official_path: Path = OFFICIAL_RESULTS_PATH,
    candidate_path: Path = CANDIDATE_RESULTS_PATH,
    sentinel_r1_path: Path = SENTINEL_R1_PATH,
    sentinel_r2_path: Path = SENTINEL_R2_PATH,
    artifact_path: Path = ARTIFACT_PATH,
) -> dict[str, Any]:
    test_cases = {
        test_case.question: test_case
        for test_case in TEST_SET
        if test_case.priority <= 2
    }
    artifact_cases = _case_map(artifact)
    official_cases = _case_map(official)
    candidate_cases = _case_map(candidate)
    r1_cases = _case_map(sentinel_r1)
    r2_cases = _case_map(sentinel_r2)
    questions = [
        test_case.question
        for test_case in TEST_SET
        if test_case.priority <= 2
        and test_case.question in artifact_cases
        and test_case.question in official_cases
        and test_case.question in candidate_cases
    ]

    rows: list[dict[str, Any]] = []
    for question in questions:
        test_case = test_cases[question]
        artifact_case = artifact_cases[question]
        official_case = official_cases[question]
        candidate_case = candidate_cases[question]
        official_context = _render(
            artifact_case, test_case, CONTEXT_STRATEGY_SELECTIVE_V5
        )
        candidate_context = _render(
            artifact_case, test_case, CONTEXT_STRATEGY_SELECTIVE_V6
        )
        official_context_summary = _context_summary(official_context)
        candidate_context_summary = _context_summary(candidate_context)
        score_deltas = {
            key: (
                _score(candidate_case, key) - _score(official_case, key)
                if _score(candidate_case, key) is not None
                and _score(official_case, key) is not None
                else None
            )
            for key in SCORE_KEYS
        }
        context_changed = (
            official_context_summary["context_sha256"]
            != candidate_context_summary["context_sha256"]
        )
        official_answer = official_case.get("answer") or ""
        candidate_answer = candidate_case.get("answer") or ""
        answer_changed = _text_sha256(official_answer) != _text_sha256(
            candidate_answer
        )
        row = {
            "question": question,
            "category": test_case.category,
            "context_changed": context_changed,
            "answer_changed": answer_changed,
            "official_context": official_context_summary,
            "candidate_context": candidate_context_summary,
            "official_answer_sha256": _text_sha256(official_answer),
            "candidate_answer_sha256": _text_sha256(candidate_answer),
            "official_scores": {
                key: _score(official_case, key) for key in SCORE_KEYS
            },
            "candidate_scores": {
                key: _score(candidate_case, key) for key in SCORE_KEYS
            },
            "score_deltas": score_deltas,
        }
        if question == MICROSOFT_RISK_QUESTION:
            row["candidate_risk_shape"] = _risk_shape(
                question, candidate_answer, candidate_context
            )
            row["official_risk_shape"] = _risk_shape(
                question, official_answer, official_context
            )
        rows.append(row)

    by_question = {row["question"]: row for row in rows}
    regressions = [
        row["question"]
        for row in rows
        if row["score_deltas"]["answer_relevancy"] is not None
        and row["score_deltas"]["answer_relevancy"] < 0
    ]
    apple_r1 = r1_cases.get(APPLE_QUALITY_QUESTION, {})
    apple_r2 = r2_cases.get(APPLE_QUALITY_QUESTION, {})
    v7_apple = candidate_cases.get(APPLE_QUALITY_QUESTION, {})
    apple_context = _render(
        artifact_cases[APPLE_QUALITY_QUESTION],
        test_cases[APPLE_QUALITY_QUESTION],
        CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    apple_selector_r1 = (sentinel_r1.get("selector_rows") or {}).get(
        APPLE_QUALITY_QUESTION, {}
    )
    apple_selector_r2 = (sentinel_r2.get("selector_rows") or {}).get(
        APPLE_QUALITY_QUESTION, {}
    )
    apple_context_hash = _context_summary(apple_context)["context_sha256"]
    apple_answer_hashes = {
        _text_sha256(apple_r1.get("answer") or ""),
        _text_sha256(v7_apple.get("answer") or ""),
    }
    gates = {
        "official_hash_pinned": _file_sha256(official_path)
        == EXPECTED_OFFICIAL_SHA256,
        "candidate_hash_pinned": _file_sha256(candidate_path)
        == EXPECTED_CANDIDATE_SHA256,
        "case_set_complete": len(rows) == 30
        and {row["question"] for row in rows}
        == {test_case.question for test_case in TEST_SET if test_case.priority <= 2},
        "non_fact_contexts_byte_identical": all(
            not row["context_changed"]
            for row in rows
            if row["category"] != "fact_lookup"
        ),
        "observed_regressions_are_expected": set(regressions)
        == set(EXPECTED_REGRESSIONS),
        "regression_contexts_unchanged": all(
            by_question[question]["context_changed"] is False
            for question in EXPECTED_REGRESSIONS
        ),
        "microsoft_risk_overdetail_observed": (
            by_question[MICROSOFT_RISK_QUESTION]["candidate_risk_shape"][
                "overdetailed"
            ]
            is True
            and by_question[MICROSOFT_RISK_QUESTION]["candidate_risk_shape"][
                "passed"
            ]
            is True
        ),
        "apple_same_answer_across_runs": len(apple_answer_hashes) == 1,
        "apple_context_same_across_runs": (
            _context_summary(apple_context)["source_boundary_parse_passed"]
            and apple_selector_r1.get("v6_context_sha256") == apple_context_hash
            and apple_selector_r2.get("v6_context_sha256") == apple_context_hash
            and apple_selector_r1.get("v6_context_sha256")
            == apple_selector_r2.get("v6_context_sha256")
        ),
        "apple_judge_variance_observed": (
            _score(apple_r1, "answer_relevancy")
            != _score(v7_apple, "answer_relevancy")
            and _score(apple_r1, "answer_relevancy") is not None
            and _score(v7_apple, "answer_relevancy") is not None
        ),
        "sentinel_replicates_available": all(
            len(document.get("cases", [])) == 7
            for document in (sentinel_r1, sentinel_r2)
        ),
    }
    return {
        "schema_version": 1,
        "audit": "answer_focus_variance_v1",
        "official": False,
        "decision": (
            "answer_focus_and_risk_granularity_are_the_next_scope; do not "
            "change retrieval or relax admission thresholds"
        ),
        "official_path": str(official_path),
        "official_sha256": _file_sha256(official_path),
        "candidate_path": str(candidate_path),
        "candidate_sha256": _file_sha256(candidate_path),
        "sentinel_r1_path": str(sentinel_r1_path),
        "sentinel_r1_sha256": _file_sha256(sentinel_r1_path),
        "sentinel_r2_path": str(sentinel_r2_path),
        "sentinel_r2_sha256": _file_sha256(sentinel_r2_path),
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "official_strategy": CONTEXT_STRATEGY_SELECTIVE_V5,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "num_cases": len(rows),
        "answer_relevancy_regression_questions": regressions,
        "cases": rows,
        "apple_same_answer_hash": next(iter(apple_answer_hashes), None),
        "apple_sentinel_r1_answer_relevancy": _score(
            apple_r1, "answer_relevancy"
        ),
        "apple_v7_answer_relevancy": _score(
            v7_apple, "answer_relevancy"
        ),
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    *,
    official_path: Path = OFFICIAL_RESULTS_PATH,
    candidate_path: Path = CANDIDATE_RESULTS_PATH,
    sentinel_r1_path: Path = SENTINEL_R1_PATH,
    sentinel_r2_path: Path = SENTINEL_R2_PATH,
    artifact_path: Path = ARTIFACT_PATH,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    """Load pinned artifacts and write the audit report."""
    official = json.loads(official_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    sentinel_r1 = json.loads(sentinel_r1_path.read_text(encoding="utf-8"))
    sentinel_r2 = json.loads(sentinel_r2_path.read_text(encoding="utf-8"))
    artifact, _ = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    report = build_report(
        official,
        candidate,
        sentinel_r1,
        sentinel_r2,
        artifact,
        official_path=official_path,
        candidate_path=candidate_path,
        sentinel_r1_path=sentinel_r1_path,
        sentinel_r2_path=sentinel_r2_path,
        artifact_path=artifact_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--official", type=Path, default=OFFICIAL_RESULTS_PATH)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_RESULTS_PATH)
    parser.add_argument("--sentinel-r1", type=Path, default=SENTINEL_R1_PATH)
    parser.add_argument("--sentinel-r2", type=Path, default=SENTINEL_R2_PATH)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(
        official_path=args.official,
        candidate_path=args.candidate,
        sentinel_r1_path=args.sentinel_r1,
        sentinel_r2_path=args.sentinel_r2,
        artifact_path=args.artifact,
        output=args.output,
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
