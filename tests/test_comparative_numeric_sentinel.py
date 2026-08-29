from scripts.run_comparative_numeric_sentinel import (
    APPLE_QUESTION,
    AWS_QUESTION,
    build_sentinel_report,
)


APPLE_CONTEXT = """[Source 1] Apple 2025 10-K
Apple Services include cloud storage and services revenue.

[Source 2] Microsoft 2025 10-K
Azure drives Microsoft's cloud revenue.
"""

AWS_CONTEXT = """[Source 1] Amazon 2025 10-K
AWS net sales increased from $107,556 million in 2024 to $128,725 million in 2025.

[Source 2] Microsoft 2025 10-K
Microsoft Cloud revenue increased 23% to $168.9 billion in fiscal year 2025.
"""


def _provider_run(apple_answer: str, aws_answer: str) -> dict:
    cases = [
        {
            "question": APPLE_QUESTION,
            "generation_status": "OK",
            "judge_status": "OK",
            "answer": apple_answer,
            "scores": {
                "faithfulness": 0.95,
                "answer_relevancy": 0.95,
                "context_precision": 0.8,
            },
            "deterministic": {
                "citation_correctness": 1.0,
                "recall_proxy": 1.0,
                "fallback_correct": True,
            },
        },
        {
            "question": AWS_QUESTION,
            "generation_status": "OK",
            "judge_status": "OK",
            "answer": aws_answer,
            "scores": {
                "faithfulness": 0.95,
                "answer_relevancy": 0.95,
                "context_precision": 0.8,
            },
            "deterministic": {
                "citation_correctness": 1.0,
                "recall_proxy": 1.0,
                "fallback_correct": True,
            },
        },
    ]
    return {
        "provider_complete": True,
        "num_selected": 2,
        "num_generation_ok": 2,
        "num_judged_ok": 2,
        "context_strategy": "selective_packed_v2",
        "cases": cases,
    }


def _contexts() -> dict[str, str]:
    return {
        APPLE_QUESTION: APPLE_CONTEXT,
        AWS_QUESTION: AWS_CONTEXT,
    }


def test_sentinel_accepts_explicit_grounded_numeric_comparison() -> None:
    report = build_sentinel_report(
        _provider_run(
            "Apple reports Services revenue including cloud storage [Source 1]. "
            "Microsoft's cloud revenue is driven by Azure [Source 2].",
            "AWS net sales increased from $107,556 million in 2024 to "
            "$128,725 million in 2025 [Source 1]. Microsoft Cloud revenue "
            "increased [Source 2].",
        ),
        _contexts(),
    )

    assert report["gate_passed"] is True
    assert report["numeric_contract"] == {
        "apple_no_derived_values": True,
        "aws_exact_values_and_periods": True,
    }


def test_sentinel_rejects_apple_derived_value_not_in_evidence() -> None:
    report = build_sentinel_report(
        _provider_run(
            "Apple Services revenue increased by $12,989 million [Source 1]. "
            "Microsoft's cloud revenue is driven by Azure [Source 2].",
            "AWS net sales increased from $107,556 million in 2024 to "
            "$128,725 million in 2025 [Source 1]. Microsoft Cloud revenue "
            "increased [Source 2].",
        ),
        _contexts(),
    )

    assert report["gate_passed"] is False
    assert report["gates"]["answer_integrity"] is False
    assert report["gates"]["numeric_contract"] is False
    apple = next(case for case in report["cases"] if case["question"] == APPLE_QUESTION)
    assert apple["answer_audit"]["unsupported_numeric_claims"] == ("$12,989",)


def test_sentinel_rejects_percentage_only_aws_answer() -> None:
    report = build_sentinel_report(
        _provider_run(
            "Apple reports Services revenue including cloud storage [Source 1]. "
            "Microsoft's cloud revenue is driven by Azure [Source 2].",
            "AWS grew 20% in 2025 [Source 1]. Microsoft Cloud revenue increased "
            "[Source 2].",
        ),
        _contexts(),
    )

    assert report["gate_passed"] is False
    assert report["gates"]["answer_integrity"] is False
    assert report["numeric_contract"]["aws_exact_values_and_periods"] is False
