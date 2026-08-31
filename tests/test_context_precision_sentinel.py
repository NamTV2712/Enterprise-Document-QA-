from __future__ import annotations

from scripts.run_context_precision_sentinel import (
    SENTINEL_QUESTIONS,
    build_report,
    sentinel_artifact_paths,
    sentinel_cases,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V3,
    CONTEXT_STRATEGY_SELECTIVE_V4,
)


def _summary(scores_by_question: dict[str, dict[str, float]]) -> dict:
    return {
        "provider_complete": True,
        "num_selected": len(SENTINEL_QUESTIONS),
        "num_generation_ok": len(SENTINEL_QUESTIONS),
        "num_judged_ok": len(SENTINEL_QUESTIONS),
        "cases": [
            {
                "question": question,
                "generation_status": "OK",
                "judge_status": "OK",
                "deterministic": {
                    "citation_correctness": 1.0,
                    "fallback_correct": True,
                    "recall_proxy": None,
                },
                "scores": scores_by_question[question],
            }
            for question in SENTINEL_QUESTIONS
        ],
    }


def test_sentinel_case_contract_is_exactly_four_known_cases() -> None:
    assert [case.question for case in sentinel_cases()] == list(SENTINEL_QUESTIONS)


def test_sentinel_replicates_use_strategy_specific_paths() -> None:
    v3 = sentinel_artifact_paths(CONTEXT_STRATEGY_SELECTIVE_V3, "r1")
    v4 = sentinel_artifact_paths(CONTEXT_STRATEGY_SELECTIVE_V4, "r2")

    assert all("_r1" in path.name for path in v3)
    assert all("_r2" in path.name for path in v4)
    assert all("context_precision_v3" in path.name for path in v3)
    assert all("context_precision_v4" in path.name for path in v4)


def test_sentinel_accepts_complete_non_regressing_candidate() -> None:
    reference = {
        question: {
            "faithfulness": 1.0,
            "answer_relevancy": 1.0,
            "context_precision": 0.5,
        }
        for question in SENTINEL_QUESTIONS
    }

    report = build_report(_summary(reference), reference)

    assert report["passed"] is True
    assert report["official"] is False


def test_sentinel_rejects_aggregate_score_regression() -> None:
    reference = {
        question: {
            "faithfulness": 1.0,
            "answer_relevancy": 1.0,
            "context_precision": 1.0,
        }
        for question in SENTINEL_QUESTIONS
    }
    candidate = {question: dict(scores) for question, scores in reference.items()}
    candidate[SENTINEL_QUESTIONS[0]]["context_precision"] = 0.5

    report = build_report(_summary(candidate), reference)

    assert report["passed"] is False
    assert report["gates"]["score_regression_passed"] is False
