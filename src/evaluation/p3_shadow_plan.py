"""Static human-reviewed retrieval plans for Priority-3 Shadow v1.

Priority-3 is a generalization shadow, not a planner-variance benchmark.  It
therefore uses a small code-owned plan contract with one direct query for each
direct case and two explicit risk-factor branches for the Visa/Mastercard
comparison.  No provider planner, ground truth, or judge output is consulted
when these plans are built.
"""

from __future__ import annotations

from typing import Any

from src.evaluation.retrieval_plan import (
    PlanQuery,
    RetrievalPlan,
    compute_plan_fingerprint,
)
from src.evaluation.test_case_selector import select_test_cases
from src.evaluation.test_set import TEST_SET, TestCase

P3_SHADOW_PLAN_SCHEMA_VERSION = 1
P3_SHADOW_PLAN_SOURCE = "priority3_shadow_v1_human_reviewed_static"
P3_SHADOW_PRIORITY = 3

_DIRECT_CASES: tuple[tuple[str, str, str], ...] = (
    ("What was Visa's total assets in fiscal year 2025?", "V", "financial_table"),
    ("What was Mastercard's total assets in fiscal year 2025?", "MA", "financial_table"),
    ("What was Eli Lilly's total assets in fiscal year 2025?", "LLY", "financial_table"),
    ("What were Chevron's total assets in fiscal years 2025 and 2024?", "CVX", "financial_table"),
    ("What were JPMorgan Chase's total assets in fiscal years 2025 and 2024?", "JPM", "financial_table"),
    ("What were ExxonMobil's total assets in fiscal years 2025 and 2024?", "XOM", "financial_table"),
    ("What was IBM's total revenue in fiscal year 2025?", "IBM", "financial_table"),
    ("What was IBM's net income in fiscal year 2025?", "IBM", "financial_table"),
    ("What were IBM's total assets in fiscal years 2025 and 2024?", "IBM", "financial_table"),
    ("What are Coca-Cola's main risk factors related to competition?", "KO", "risk_factors"),
    ("How does Morgan Stanley describe its core business?", "MS", "business"),
    ("How does McDonald's describe its restaurant business system?", "MCD", "business"),
    ("What are Intel's main semiconductor businesses?", "INTC", "business"),
    ("What is Costco's principal business?", "COST", "business"),
    ("How does GE Aerospace describe its core business?", "GE", "business"),
    ("What are Honeywell's four reportable business segments?", "HON", "business"),
    ("How did Chevron's total assets change from fiscal year 2024 to fiscal year 2025?", "CVX", "financial_table"),
    ("How did JPMorgan Chase's total assets change from fiscal year 2024 to fiscal year 2025?", "JPM", "financial_table"),
    ("How did ExxonMobil's total assets change from fiscal year 2024 to fiscal year 2025?", "XOM", "financial_table"),
    ("How did IBM's total revenue change from fiscal year 2024 to fiscal year 2025?", "IBM", "financial_table"),
    ("How did RTX's total net sales trend across fiscal years 2023, 2024, and 2025?", "RTX", "financial_table"),
)

_COMPARATIVE_QUESTION = "Compare Visa and Mastercard's business risk factors."


def _direct_plan(question: str, ticker: str, section: str) -> RetrievalPlan:
    return RetrievalPlan(
        question=question,
        category=next(case.category for case in TEST_SET if case.question == question),
        route="direct",
        queries=(
            PlanQuery(
                effective_query=question,
                ticker=ticker,
                section=section,
                query_source="human_reviewed_p3",
            ),
        ),
    )


def _comparative_plan() -> RetrievalPlan:
    return RetrievalPlan(
        question=_COMPARATIVE_QUESTION,
        category="comparative",
        route="decomposed",
        queries=(
            PlanQuery(
                effective_query="Visa business risk factors",
                ticker="V",
                section="risk_factors",
                query_source="human_reviewed_p3",
            ),
            PlanQuery(
                effective_query="Mastercard business risk factors",
                ticker="MA",
                section="risk_factors",
                query_source="human_reviewed_p3",
            ),
        ),
    )


def build_priority3_shadow_plans() -> list[RetrievalPlan]:
    """Return the complete P3 plan set in test-set order."""
    direct = {question: _direct_plan(question, ticker, section)
              for question, ticker, section in _DIRECT_CASES}
    direct[_COMPARATIVE_QUESTION] = _comparative_plan()
    selected = select_test_cases(TEST_SET, priority=P3_SHADOW_PRIORITY, exact_priority=True)
    return [direct[case.question] for case in selected.cases]


def validate_priority3_shadow_plans(
    plans: list[RetrievalPlan],
    test_cases: list[TestCase] | None = None,
) -> None:
    """Fail closed unless the exact reviewed P3 contract is present."""
    expected_cases = test_cases or list(
        select_test_cases(TEST_SET, priority=P3_SHADOW_PRIORITY, exact_priority=True).cases
    )
    expected_questions = [case.question for case in expected_cases]
    if len(plans) != len(expected_questions):
        raise ValueError(f"Expected {len(expected_questions)} P3 plans, found {len(plans)}")
    if [plan.question for plan in plans] != expected_questions:
        raise ValueError("P3 plans must match the selected test cases in test-set order")
    if any(plan.question not in {case.question for case in expected_cases} for plan in plans):
        raise ValueError("P3 plans contain an unknown question")
    for plan, case in zip(plans, expected_cases, strict=True):
        if plan.category != case.category:
            raise ValueError(f"P3 plan category mismatch for {plan.question!r}")
        if not plan.queries or any(not query.effective_query.strip() for query in plan.queries):
            raise ValueError(f"P3 plan has an empty query: {plan.question!r}")
        if any(query.query_source != "human_reviewed_p3" for query in plan.queries):
            raise ValueError(f"P3 plan is not marked human-reviewed: {plan.question!r}")
        if plan.question == _COMPARATIVE_QUESTION:
            if plan.route != "decomposed" or len(plan.queries) != 2:
                raise ValueError("Visa/Mastercard comparison must have two branches")
            branches = [(query.ticker, query.section) for query in plan.queries]
            if branches != [("V", "risk_factors"), ("MA", "risk_factors")]:
                raise ValueError("Visa/Mastercard branches drifted from the P3 contract")
        elif plan.route != "direct" or len(plan.queries) != 1:
            raise ValueError(f"P3 non-comparative plan must be direct: {plan.question!r}")


P3_SHADOW_PLANS = build_priority3_shadow_plans()
validate_priority3_shadow_plans(P3_SHADOW_PLANS)
P3_SHADOW_PLAN_FINGERPRINT = compute_plan_fingerprint(P3_SHADOW_PLANS)


def priority3_shadow_plan_provenance() -> dict[str, Any]:
    """Return provenance that cannot be mistaken for live planner output."""
    return {
        "kind": "static_human_reviewed_plan",
        "source": P3_SHADOW_PLAN_SOURCE,
        "schema_version": P3_SHADOW_PLAN_SCHEMA_VERSION,
        "plan_fingerprint": P3_SHADOW_PLAN_FINGERPRINT,
        "provider_planner_used": False,
        "ground_truth_used": False,
        "variance_note": "static P3 shadow contract; live planner variance is not measured",
    }
