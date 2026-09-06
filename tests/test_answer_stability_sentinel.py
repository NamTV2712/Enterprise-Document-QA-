import json
from pathlib import Path
from tests.conftest import skip_without_data

from scripts.run_answer_stability_sentinel import (
    ENUMERATION_CONTROL_QUESTIONS,
    FACT_QUESTIONS,
    NUMERIC_CANARY_QUESTIONS,
    REGRESSION_QUESTIONS,
    RISK_CONTROL_QUESTIONS,
    RISK_TARGET_QUESTIONS,
    SENTINEL_QUESTIONS,
    _selector_rows,
)


def test_sentinel_contract_contains_focus_targets_and_controls() -> None:
    assert len(SENTINEL_QUESTIONS) == 8
    assert len(REGRESSION_QUESTIONS) == 8
    assert len(RISK_TARGET_QUESTIONS) == 2
    assert len(RISK_CONTROL_QUESTIONS) == 3
    assert len(ENUMERATION_CONTROL_QUESTIONS) == 1
    assert len(NUMERIC_CANARY_QUESTIONS) == 2
    assert len(FACT_QUESTIONS) == 0
    assert REGRESSION_QUESTIONS.isdisjoint(FACT_QUESTIONS)


@skip_without_data(
    "data/eval_artifacts/phase1_priority2.json",
)
def test_sentinel_selector_is_provider_free_and_preserves_regression_contexts() -> None:
    artifact = json.loads(
        Path("data/eval_artifacts/phase1_priority2.json").read_text(
            encoding="utf-8"
        )
    )
    rows = _selector_rows(artifact)

    assert all(
        rows[question]["v5_v6_context_identical"]
        and rows[question]["selector_safe"]
        and rows[question]["selector_one_source"]
        for question in SENTINEL_QUESTIONS
    )
