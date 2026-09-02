import json
from pathlib import Path

from scripts.run_answer_stability_sentinel import (
    FACT_QUESTIONS,
    REGRESSION_QUESTIONS,
    SENTINEL_QUESTIONS,
    _selector_rows,
)


def test_sentinel_contract_contains_three_regressions_and_four_fact_targets() -> None:
    assert len(SENTINEL_QUESTIONS) == 7
    assert len(REGRESSION_QUESTIONS) == 3
    assert len(FACT_QUESTIONS) == 4
    assert REGRESSION_QUESTIONS.isdisjoint(FACT_QUESTIONS)


def test_sentinel_selector_is_provider_free_and_preserves_regression_contexts() -> None:
    artifact = json.loads(
        Path("data/eval_artifacts/phase1_priority2.json").read_text(
            encoding="utf-8"
        )
    )
    rows = _selector_rows(artifact)

    assert all(rows[question]["v5_v6_context_identical"] for question in REGRESSION_QUESTIONS)
    assert all(
        rows[question]["selector_safe"]
        and rows[question]["selector_one_source"]
        for question in FACT_QUESTIONS
    )
