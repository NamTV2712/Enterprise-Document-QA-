"""Fixed retrieval plans for the deterministic two-phase evaluation.

A plan freezes, per test case, exactly how evidence is retrieved: the
route (direct or decomposed), the ordered effective queries with their
ticker/section filters, and the provenance of each query string. Plans
are derived from the frozen official evaluation artifact and validated
against the selected test set; a missing or extra plan is a hard error
so Phase 1 can never fall back to an LLM planner or rewriter.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from src.evaluation.test_set import TestCase

PLAN_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PlanQuery:
    """One executed retrieval query inside a plan."""

    effective_query: str
    ticker: str | None
    section: str | None
    query_source: Literal[
        "original_question",
        "saved_subquery",
        "original_proxy_missing_rewrite",
        "planner_snapshot",
    ]


@dataclass(frozen=True)
class RetrievalPlan:
    """The frozen retrieval route for one test case."""

    question: str
    category: str
    route: Literal["direct", "decomposed"]
    queries: tuple[PlanQuery, ...]


def plans_to_payload(plans: list[RetrievalPlan]) -> list[dict[str, Any]]:
    """Canonical JSON-ready representation used for hashing and artifacts."""
    return [
        {
            "question": plan.question,
            "category": plan.category,
            "route": plan.route,
            "queries": [
                {
                    "effective_query": q.effective_query,
                    "ticker": q.ticker,
                    "section": q.section,
                    "query_source": q.query_source,
                }
                for q in plan.queries
            ],
        }
        for plan in plans
    ]


def compute_plan_fingerprint(plans: list[RetrievalPlan]) -> str:
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plans": plans_to_payload(plans),
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def validate_plans_cover(
    plans: list[RetrievalPlan],
    test_cases: list[TestCase],
) -> None:
    """Fail closed unless plans and the selected test set match exactly."""
    plan_questions = [plan.question for plan in plans]
    case_questions = [case.question for case in test_cases]

    duplicates = sorted({
        question for question in plan_questions
        if plan_questions.count(question) > 1
    })
    if duplicates:
        raise ValueError(f"Duplicate retrieval plans for questions: {duplicates}")

    missing = [q for q in case_questions if q not in set(plan_questions)]
    if missing:
        raise ValueError(
            "Missing fixed retrieval plans; refusing to run any LLM planner. "
            f"Add explicit plans for: {missing}"
        )
    extra = [q for q in plan_questions if q not in set(case_questions)]
    if extra:
        raise ValueError(
            f"Retrieval plans do not match the selected test set; extra: {extra}"
        )


def validate_plan_filters(
    plans: list[RetrievalPlan],
    allowed_tickers: set[str],
    allowed_sections: set[str],
) -> None:
    """Reject plans referencing tickers or sections outside the corpus."""
    for plan in plans:
        for query in plan.queries:
            if query.ticker is not None and query.ticker not in allowed_tickers:
                raise ValueError(
                    f"Plan for {plan.question!r} references unknown "
                    f"ticker {query.ticker!r}"
                )
            if query.section is not None and query.section not in allowed_sections:
                raise ValueError(
                    f"Plan for {plan.question!r} references unknown "
                    f"section {query.section!r}"
                )
