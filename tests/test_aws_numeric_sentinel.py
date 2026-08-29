from scripts.run_aws_numeric_sentinel import (
    AWS_QUESTION,
    build_sentinel_report,
)


CONTEXT = """[Source 1] Amazon 2025 10-K
AWS net sales increased from $107,556 million in 2024 to $128,725 million in 2025.

[Source 2] Microsoft 2025 10-K
Microsoft Cloud revenue increased 23% to $168.9 billion in fiscal year 2025.
"""


def _provider_run(answer: str) -> dict:
    return {
        "provider_complete": True,
        "num_selected": 1,
        "num_generation_ok": 1,
        "num_judged_ok": 1,
        "cases": [
            {
                "question": AWS_QUESTION,
                "generation_status": "OK",
                "judge_status": "OK",
                "answer": answer,
                "scores": {
                    "faithfulness": 1.0,
                    "answer_relevancy": 0.95,
                    "context_precision": 0.8,
                },
                "deterministic": {
                    "citation_correctness": 1.0,
                    "recall_proxy": 1.0,
                    "fallback_correct": True,
                },
            }
        ],
    }


def test_sentinel_gate_passes_exact_grounded_period_value_answer() -> None:
    answer = (
        "AWS net sales rose from $107,556 million in 2024 to $128,725 "
        "million in 2025 [Source 1]. Microsoft Cloud revenue also increased "
        "[Source 2]."
    )
    report = build_sentinel_report(_provider_run(answer), CONTEXT)

    assert report["official"] is False
    assert report["gate_passed"] is True
    assert all(report["answer_values"].values())
    assert all(report["answer_periods"].values())
    assert report["answer_audit"]["unsupported_numeric_claims"] == ()


def test_sentinel_gate_rejects_percentage_only_numeric_substitution() -> None:
    answer = "AWS grew 20% in 2025 [Source 1]."
    report = build_sentinel_report(_provider_run(answer), CONTEXT)

    assert report["gate_passed"] is False
    assert report["gates"]["answer_integrity"] is False
    assert report["integrity"]["exact_values_present"] is False
    assert report["integrity"]["no_unsupported_numeric_claims"] is False
