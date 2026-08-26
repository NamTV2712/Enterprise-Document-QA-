"""Frozen planner-snapshot plan overrides for evaluation Phase 1.

The stale llama-era frozen plan for the AAPL-vs-AMZN revenue comparison
filtered ``financial_statements``, which defeats structured-lookup
promotion and produced EPS-table noise on the Amazon branch. The live
``openai/gpt-oss-120b`` planner instead selects ``financial_table``,
and executing that exact plan promotes the true "Total net sales"
rows at score 10.0 on both branches.

The evaluation contract pins fiscal year 2024 inside the question
itself, resolving the earlier year ambiguity: a latest-year answer can
no longer satisfy an acceptance that checks FY2024 totals. The current
snapshot below was re-captured from one schema-validated planner call
against the FY2024 question; it keeps ``financial_table`` on both
branches and adds explicit fiscal-year wording to each subquery.

This module freezes that planner snapshot into versioned code so Phase 1
is reproducible. Provenance is explicit: this is a SNAPSHOT of one
planner output, not a measurement of per-request planner variance.

Nothing else in the official N=30 plan set is overridden.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.evaluation.retrieval_plan import (
    PlanQuery,
    RetrievalPlan,
    plans_to_payload,
)

OVERRIDE_QUESTION = (
    "Which company, Apple or Amazon, had higher total revenue in "
    "fiscal year 2024?"
)

# Verbatim validated output of the single captured planner call for
# OVERRIDE_QUESTION above (captured 2026-08-26 after the year contract
# change; see scripts/diagnostics/planner_wording_check.json).
RAW_PLANNER_OUTPUT: dict[str, Any] = {
    "needs_decomposition": True,
    "sub_queries": [
        {
            "query": "Apple total revenue fiscal year 2024",
            "ticker": "AAPL",
            "section": "financial_table",
        },
        {
            "query": "Amazon total revenue fiscal year 2024",
            "ticker": "AMZN",
            "section": "financial_table",
        },
    ],
}

PLANNER_MODEL = "openai/gpt-oss-120b"
PLANNER_MAX_TOKENS = 700


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def compute_planner_provenance() -> dict[str, Any]:
    """Identity of the planner conditions behind the snapshot."""
    from src.generation.query_decomposer import (
        DECOMPOSE_SYSTEM_PROMPT,
        SUPPORTED_TICKERS,
        VALID_SECTIONS,
    )

    return {
        "kind": "live_planner_snapshot",
        # A frozen snapshot of current planner behavior; per-request
        # planner variance is intentionally NOT measured by benchmarks
        # built from these plans.
        "variance_note": (
            "snapshot of one planner call; runtime planner variance is "
            "not represented in this benchmark"
        ),
        "model": PLANNER_MODEL,
        "temperature": 0,
        "max_tokens": PLANNER_MAX_TOKENS,
        "prompt_schema_sha256": canonical_sha256({
            "system_prompt": DECOMPOSE_SYSTEM_PROMPT,
            "user_template": "Question: {question}",
            "supported_tickers": sorted(SUPPORTED_TICKERS),
            "valid_sections": sorted(VALID_SECTIONS),
        }),
        "raw_plan_sha256": canonical_sha256(RAW_PLANNER_OUTPUT),
    }


def build_override_plan() -> RetrievalPlan:
    sub_queries = RAW_PLANNER_OUTPUT["sub_queries"]
    return RetrievalPlan(
        question=OVERRIDE_QUESTION,
        category="comparative",
        route="decomposed",
        queries=tuple(
            PlanQuery(
                effective_query=sq["query"],
                ticker=sq["ticker"],
                section=sq["section"],
                query_source="planner_snapshot",
            )
            for sq in sub_queries
        ),
    )


def apply_frozen_plan_overrides(
    plans: list[RetrievalPlan],
    selected_questions: set[str],
) -> tuple[list[RetrievalPlan], dict[str, Any]]:
    """Replace or inject overrides for code-owned selected questions.

    Phase 1 supports category-filtered runs, so an override target may be
    legitimately absent from ``plans`` AND from ``selected_questions``;
    in that case nothing is applied. When an override question IS
    selected it may still have no legacy plan — for example after the
    evaluation contract renamed the FY2024 comparative case, no official-
    artifact record exists under the new wording — so the code-owned
    snapshot plan is injected instead of failing. Coverage against the
    selected test set is still enforced by ``validate_plans_cover``.
    """
    overrides = {build_override_plan().question: build_override_plan()}
    replaced: list[RetrievalPlan] = []
    applied_questions: list[str] = []

    for plan in plans:
        override = overrides.get(plan.question)
        if override is None:
            replaced.append(plan)
        else:
            replaced.append(override)
            applied_questions.append(plan.question)

    present = {plan.question for plan in replaced}
    for question, override in overrides.items():
        if question in selected_questions and question not in present:
            replaced.append(override)
            applied_questions.append(question)

    provenance = {
        "plan_overrides": {
            question: compute_planner_provenance()
            for question in applied_questions
        }
    }
    return replaced, provenance


def override_plan_payloads() -> list[dict[str, Any]]:
    return plans_to_payload([build_override_plan()])
