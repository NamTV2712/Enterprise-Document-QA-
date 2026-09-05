import re

from src.evaluation.evidence_contract_v3 import (
    CALIBRATION_FIXTURES_SHA256,
    DEPENDENCY_QUESTION,
    PROFILE_FINGERPRINT,
    RUBRIC,
    build_judge_prompt,
    calibration_cases,
    compute_judge_binding_v3,
    reference_for,
)
from src.evaluation.test_set import TEST_SET


def test_profile_has_six_frozen_calibration_cases_and_no_missing_labels() -> None:
    cases = calibration_cases()
    assert len(cases) == 6
    assert {case["id"] for case in cases} == {
        "qualified-bounded-disclosure",
        "ranking-with-compatible-share",
        "ranking-without-share",
        "refusal-with-compatible-share",
        "risk-complete-primary-groups",
        "risk-missing-primary-group",
    }
    assert all(isinstance(case["expected"], dict) for case in cases)
    assert CALIBRATION_FIXTURES_SHA256.startswith("sha256:")
    assert PROFILE_FINGERPRINT.startswith("sha256:")


def test_v3_judge_prompt_contains_reference_and_actual_context_but_not_fixture_labels() -> None:
    case = calibration_cases()[0]
    prompt = build_judge_prompt(
        case["question"], case["answer"], case["context"], reference_for(case["question"])
    )
    assert "Evidence Contract v3" in prompt
    assert case["context"] in prompt
    assert '"expected"' not in prompt
    assert "qualified-bounded-disclosure" not in prompt
    assert "full filings lack" in prompt


def test_reference_override_is_versioned_and_legacy_reference_remains_available() -> None:
    legacy = next(case.ground_truth for case in TEST_SET if case.question == DEPENDENCY_QUESTION)
    current = reference_for(DEPENDENCY_QUESTION)
    assert current != legacy
    assert "evidence-contract-v3" in current
    assert "does not infer a winner" in current


def test_judge_binding_changes_with_context_reference_or_answer() -> None:
    case = calibration_cases()[0]
    kwargs = {
        "generation_binding": "sha256:" + "a" * 64,
        "question": case["question"],
        "answer": case["answer"],
        "context": case["context"],
        "reference": reference_for(case["question"]),
        "judge_model": "test-model",
        "prompt_sha256": "sha256:" + "b" * 64,
        "judge_max_tokens": 1024,
    }
    original = compute_judge_binding_v3(**kwargs)
    for field in ("answer", "context", "reference", "prompt_sha256"):
        changed = dict(kwargs)
        changed[field] = str(changed[field]) + " changed"
        assert compute_judge_binding_v3(**changed) != original
