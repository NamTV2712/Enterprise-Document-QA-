from __future__ import annotations

from scripts.run_fact_evidence_sufficiency_sentinel import (
    SENTINEL_QUESTIONS,
    build_report,
)


def _summary() -> dict:
    return {
        "official": False,
        "provider_complete": True,
        "context_strategy": "selective_packed_v6_fact_candidate",
        "binding": "sha256:binding",
        "num_selected": 4,
        "num_generation_ok": 4,
        "num_judged_ok": 4,
        "period_value_corrections": {
            question: {
                "applicable": False,
                "final_passed": True,
                "final_grounding_passed": True,
                "final_unsupported_numeric_claims": [],
            }
            for question in SENTINEL_QUESTIONS
        },
        "cases": [
            {
                "question": question,
                "generation_status": "OK",
                "judge_status": "OK",
                "answer": "Answer [Source 1].",
                "deterministic": {
                    "citation_correctness": 1.0,
                    "recall_proxy": 1.0,
                    "fallback_correct": True,
                },
                "scores": {
                    "faithfulness": 1.0,
                    "answer_relevancy": 1.0,
                    "context_precision": 1.0,
                },
            }
            for question in SENTINEL_QUESTIONS
        ],
    }


def _reference() -> dict[str, dict[str, float]]:
    return {
        question: {
            "faithfulness": 1.0,
            "answer_relevancy": 0.95,
            "context_precision": 0.5,
        }
        for question in SENTINEL_QUESTIONS
    }


def _selectors() -> dict[str, dict]:
    return {
        question: {
            "safe": True,
            "source_count": 1,
            "selector_tier": "structured_exact",
            "context_sha256": "sha256:context",
        }
        for question in SENTINEL_QUESTIONS
    }


def test_fact_sentinel_report_passes_registered_gates() -> None:
    report = build_report(_summary(), _reference(), _selectors(), "r1")

    assert report["passed"] is True
    assert report["candidate_aggregate"]["context_precision"] == 1.0
    assert all(report["case_gates"][question]["completion_ok"] for question in SENTINEL_QUESTIONS)


def test_fact_sentinel_report_rejects_incomplete_provider_coverage() -> None:
    summary = _summary()
    summary["num_judged_ok"] = 3

    report = build_report(summary, _reference(), _selectors(), "r1")

    assert report["passed"] is False
    assert report["gates"]["provider_complete"] is False
