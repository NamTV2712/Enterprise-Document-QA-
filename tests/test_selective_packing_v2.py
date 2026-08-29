from __future__ import annotations

from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V5,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    CONTEXT_STRATEGY_SELECTIVE,
    CONTEXT_STRATEGY_SELECTIVE_V2,
    effective_case_context_strategy,
    render_case_context,
)
from src.evaluation.generation_checkpoint import build_evidence_context


def _case(category: str) -> dict:
    return {
        "question": "Example question",
        "category": category,
        "queries": [
            {
                "query": {"effective_query": "example", "ticker": "AAPL"},
                "chunks": [
                    {
                        "chunk_id": "AAPL_0",
                        "citation": "AAPL filing",
                        "text": "Primary evidence.",
                        "score": 2.0,
                    },
                    {
                        "chunk_id": "AAPL_1",
                        "citation": "AAPL filing",
                        "text": "Additional evidence.",
                        "score": 1.0,
                    },
                ],
            }
        ],
    }


def test_selective_v2_resolves_category_policy() -> None:
    assert effective_case_context_strategy(
        CONTEXT_STRATEGY_SELECTIVE_V2, "fact_lookup"
    ) == CONTEXT_STRATEGY_ROUTE_AWARE
    assert effective_case_context_strategy(
        CONTEXT_STRATEGY_SELECTIVE_V2, "multi_hop"
    ) == CONTEXT_STRATEGY_ROUTE_AWARE
    assert effective_case_context_strategy(
        CONTEXT_STRATEGY_SELECTIVE_V2, "summary"
    ) == CONTEXT_STRATEGY_ROUTE_AWARE
    assert effective_case_context_strategy(
        CONTEXT_STRATEGY_SELECTIVE_V2, "comparative"
    ) == CONTEXT_STRATEGY_COMPARATIVE_V5
    assert effective_case_context_strategy(
        CONTEXT_STRATEGY_SELECTIVE_V2, "enumeration"
    ) == CONTEXT_STRATEGY_FULL_EVIDENCE
    assert effective_case_context_strategy(
        CONTEXT_STRATEGY_SELECTIVE_V2, "out_of_corpus"
    ) == CONTEXT_STRATEGY_FULL_EVIDENCE


def test_selective_v2_preserves_selective_policy_for_noncomparative_case() -> None:
    case = _case("fact_lookup")

    assert render_case_context(
        case,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
    ) == render_case_context(
        case,
        strategy=CONTEXT_STRATEGY_SELECTIVE,
    )


def test_selective_v2_preserves_v5_policy_for_comparative_case() -> None:
    case = _case("comparative")

    assert render_case_context(
        case,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
    ) == render_case_context(
        case,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V5,
    )


def test_composite_full_category_is_byte_identical() -> None:
    case = _case("enumeration")

    assert render_case_context(
        case,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
    ) == build_evidence_context(case)
