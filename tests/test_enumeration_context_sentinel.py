from scripts.run_enumeration_context_sentinel import (
    SENTINEL_QUESTIONS,
    build_report,
)


def _summary(context_precision: float = 0.75) -> dict:
    cases = [
        {
            "question": question,
            "generation_status": "OK",
            "judge_status": "OK",
            "scores": {
                "faithfulness": 1.0,
                "answer_relevancy": 1.0,
                "context_precision": context_precision,
            },
            "deterministic": {
                "citation_correctness": 1.0,
                "fallback_correct": True,
                "recall_proxy": 1.0,
            },
        }
        for question in SENTINEL_QUESTIONS
    ]
    return {
        "provider_complete": True,
        "num_selected": 4,
        "num_generation_ok": 4,
        "num_judged_ok": 4,
        "cases": cases,
        "period_value_corrections": {
            question: {
                "applicable": False,
                "correction_attempted": False,
                "final_passed": True,
                "final_grounding_passed": True,
            }
            for question in SENTINEL_QUESTIONS
        },
    }


def _reference() -> dict[str, dict[str, float]]:
    return {
        question: {
            "faithfulness": 1.0,
            "answer_relevancy": 0.9,
            "context_precision": 0.6,
        }
        for question in SENTINEL_QUESTIONS
    }


def test_sentinel_requires_strict_context_precision_improvement() -> None:
    report = build_report(_summary(), _reference(), "r1")

    assert report["passed"]
    assert report["gates"]["aggregate_context_precision_strict_improvement"]


def test_sentinel_rejects_one_case_semantic_regression() -> None:
    summary = _summary()
    summary["cases"][0]["scores"]["answer_relevancy"] = 0.8

    report = build_report(summary, _reference(), "r1")

    assert not report["passed"]
    assert not report["gates"]["per_case_semantic_non_regression"]
