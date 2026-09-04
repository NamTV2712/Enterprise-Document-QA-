from __future__ import annotations

import pytest

from scripts.run_evaluation_phase2 import select_questions
from src.evaluation.p3_shadow_plan import (
    P3_SHADOW_PLAN_FINGERPRINT,
    P3_SHADOW_PLANS,
    priority3_shadow_plan_provenance,
    validate_priority3_shadow_plans,
)
from src.evaluation.test_case_selector import select_test_cases
from src.evaluation.test_set import TEST_SET


def test_shared_selector_keeps_cumulative_p2_and_exact_p3_scopes() -> None:
    p2 = select_test_cases(TEST_SET, priority=2)
    p3 = select_test_cases(TEST_SET, priority=3, exact_priority=True)

    assert len(p2.cases) == 30
    assert len(p3.cases) == 22
    assert all(case.priority <= 2 for case in p2.cases)
    assert all(case.priority == 3 for case in p3.cases)
    assert p3.provenance()["selection_scope"] == "priority == 3"


def test_phase2_selector_rejects_missing_evidence_for_exact_scope() -> None:
    p3 = select_test_cases(TEST_SET, priority=3, exact_priority=True)
    artifact = {"cases": [{"question": p3.questions[0]}]}

    with pytest.raises(RuntimeError, match="lacks evidence"):
        select_questions(artifact, priority=3, exact_priority=True)


def test_priority3_contract_has_exact_shape_and_static_provenance() -> None:
    validate_priority3_shadow_plans(P3_SHADOW_PLANS)

    assert len(P3_SHADOW_PLANS) == 22
    assert sum(plan.route == "direct" for plan in P3_SHADOW_PLANS) == 21
    assert P3_SHADOW_PLAN_FINGERPRINT.startswith("sha256:")
    provenance = priority3_shadow_plan_provenance()
    assert provenance["kind"] == "static_human_reviewed_plan"
    assert provenance["provider_planner_used"] is False
    assert provenance["ground_truth_used"] is False

    comparative = next(
        plan for plan in P3_SHADOW_PLANS
        if plan.question == "Compare Visa and Mastercard's business risk factors."
    )
    assert [(q.ticker, q.section) for q in comparative.queries] == [
        ("V", "risk_factors"),
        ("MA", "risk_factors"),
    ]


def test_p3_contract_pins_periods_and_forbids_calculated_deltas() -> None:
    by_question = {case.question: case for case in TEST_SET}
    assert "fiscal year 2025" in by_question[
        "What was Visa's total assets in fiscal year 2025?"
    ].ground_truth
    assert "fiscal year 2025" in by_question[
        "What was Mastercard's total assets in fiscal year 2025?"
    ].ground_truth
    assert "fiscal year 2025" in by_question[
        "What was Eli Lilly's total assets in fiscal year 2025?"
    ].ground_truth

    for question in (
        "How did Chevron's total assets change from fiscal year 2024 to fiscal year 2025?",
        "How did JPMorgan Chase's total assets change from fiscal year 2024 to fiscal year 2025?",
        "How did ExxonMobil's total assets change from fiscal year 2024 to fiscal year 2025?",
    ):
        ground_truth = by_question[question].ground_truth
        assert "increase of $" not in ground_truth
        assert "decrease of $" not in ground_truth

    honeywell = by_question["What are Honeywell's four reportable business segments?"]
    assert set(honeywell.required_keywords) == {
        "Aerospace Technologies",
        "Industrial Automation",
        "Building Automation",
        "Energy and Sustainability Solutions",
    }
