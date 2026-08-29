"""Tests for route-aware context packing over frozen evidence."""

from __future__ import annotations

import pytest

from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    PackedContext,
    collect_entries,
    pack_case_context,
    render_packed_blocks,
)


def _chunk(chunk_id: str, text: str, score: float, ticker: str | None = None) -> dict:
    entry = {
        "chunk_id": chunk_id,
        "citation": f"{chunk_id} citation",
        "text": text,
        "score": score,
    }
    if ticker:
        entry["ticker"] = ticker
    return entry


def _case(queries: list[dict], category: str) -> dict:
    return {
        "category": category,
        "queries": [
            {
                "query": {"effective_query": q["query"], "ticker": q.get("ticker")},
                "chunks": q["chunks"],
            }
            for q in queries
        ],
        "final_chunk_ids": [
            c["chunk_id"] for q in queries for c in q["chunks"]
        ],
    }


def test_full_evidence_strategy_keeps_everything_in_source_order() -> None:
    a = _chunk("A_c0", "alpha", 1.0)
    b = _chunk("B_c0", "beta", 2.0)
    case = _case(
        [
            {"query": "q1", "ticker": "AAPL", "chunks": [a]},
            {"query": "q2", "ticker": None, "chunks": [b, a]},  # duplicate
        ],
        "fact_lookup",
    )

    packed = pack_case_context(case, strategy=CONTEXT_STRATEGY_FULL_EVIDENCE)

    assert [e["chunk_id"] for e in packed.kept] == ["A_c0", "B_c0"]
    assert packed.dropped == []


def test_fact_lookup_keeps_structured_hit_and_drops_noise() -> None:
    primary = _chunk("AAPL_t0", "Total net sales 391,035", 10.0, "AAPL")
    noise_low = _chunk("AAPL_n1", "unrelated narrative about iPhone mix", 0.4)
    support = _chunk("AAPL_s2", "net sales discussion paragraph", 3.2)
    case = _case(
        [{"query": "revenue", "ticker": "AAPL",
          "chunks": [primary, noise_low, support]}],
        "fact_lookup",
    )

    packed = pack_case_context(
        case,
        required_keywords=["391,035"],
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )

    kept_ids = [e["chunk_id"] for e in packed.kept]
    # Primary position plus the exact structured promotion; the low-score
    # noise chunk is dropped because nothing requires it.
    assert kept_ids == ["AAPL_t0", "AAPL_s2"]
    assert [e["chunk_id"] for e in packed.dropped] == ["AAPL_n1"]
    assert packed.uncovered_keywords == []


def test_comparative_preserves_one_chunk_per_expected_ticker() -> None:
    aapl_hit = _chunk("AAPL_t0", "Apple total net sales 391,035", 10.0, "AAPL")
    amzn_weak = _chunk("AMZN_t0", "Amazon total net sales 637,959", -0.5, "AMZN")
    amzn_extra = _chunk("AMZN_x1", "Amazon segments narrative", 8.0, "AMZN")
    case = _case(
        [
            {"query": "apple revenue", "ticker": "AAPL", "chunks": [aapl_hit]},
            {"query": "amazon revenue", "ticker": "AMZN",
             "chunks": [amzn_extra, amzn_weak]},
        ],
        "comparative",
    )

    packed = pack_case_context(
        case,
        required_keywords=["391,035", "637,959"],
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )

    kept_ids = {e["chunk_id"] for e in packed.kept}
    # The weak AMZN table row is mandatory: it is AMZN's only evidence for
    # its expected ticker and carries a required number.
    assert "AMZN_t0" in kept_ids
    assert "AAPL_t0" in kept_ids
    assert packed.uncovered_keywords == []
    # Source order is restored across queries.
    order = [e["chunk_id"] for e in packed.kept]
    assert order.index("AAPL_t0") < order.index("AMZN_t0")


def test_multi_hop_keeps_chunks_carrying_required_numbers() -> None:
    strong_wrong = _chunk("MSFT_n0", "cloud commercial narrative", 9.0)
    weak_fact = _chunk("MSFT_t1", "Total assets 512,163 619,003", -1.0)
    case = _case(
        [{"query": "total assets yoy", "ticker": "MSFT",
          "chunks": [strong_wrong, weak_fact]}],
        "multi_hop",
    )

    packed = pack_case_context(
        case,
        required_keywords=["512,163", "619,003"],
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )

    kept_ids = [e["chunk_id"] for e in packed.kept]
    assert "MSFT_t1" in kept_ids
    assert "MSFT_n0" in kept_ids  # primary position


def test_summary_fills_to_target_by_score() -> None:
    entries = [
        _chunk("S_c0", "risk one", 1.0),
        _chunk("S_c1", "risk two", 5.0),
        _chunk("S_c2", "risk three", 4.0),
        _chunk("S_c3", "risk four", 3.0),
        _chunk("S_c4", "risk five", 0.2),
    ]
    case = _case(
        [{"query": "risks", "ticker": "AAPL", "chunks": entries}],
        "summary",
    )

    packed = pack_case_context(
        case,
        required_keywords=[],
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )

    assert len(packed.kept) == 4
    assert "S_c4" in [e["chunk_id"] for e in packed.dropped]


def test_out_of_corpus_keeps_only_primary() -> None:
    entries = [_chunk("N_c0", "irrelevant", 1.0), _chunk("N_c1", "irrelevant", 0.5)]
    case = _case([{"query": "netflix", "ticker": None, "chunks": entries}], "out_of_corpus")

    packed = pack_case_context(case, strategy=CONTEXT_STRATEGY_ROUTE_AWARE)

    assert [e["chunk_id"] for e in packed.kept] == ["N_c0"]


def test_uncovered_keyword_reported_when_absent_everywhere() -> None:
    only = _chunk("X_c0", "no numbers here", 2.0)
    case = _case([{"query": "q", "ticker": None, "chunks": [only]}], "fact_lookup")

    packed = pack_case_context(
        case,
        required_keywords=["999,999"],
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )

    assert packed.uncovered_keywords == ["999,999"]


def test_packing_is_deterministic_and_renders_blocks() -> None:
    entries = [_chunk(f"C_c{i}", f"text {i} kw", 10.0 - i) for i in range(6)]
    case = _case([{"query": "q", "ticker": None, "chunks": entries}], "summary")

    first = pack_case_context(case, required_keywords=["kw"], strategy=CONTEXT_STRATEGY_ROUTE_AWARE)
    second = pack_case_context(case, required_keywords=["kw"], strategy=CONTEXT_STRATEGY_ROUTE_AWARE)

    assert first.kept_ids == second.kept_ids
    blocks = render_packed_blocks(first).split("\n\n")
    assert blocks[0].startswith("[Source 1] C_c0 citation")
    assert isinstance(first, PackedContext)


def test_collect_entries_deduplicates_across_queries() -> None:
    a = _chunk("A_c0", "alpha", 1.0)
    b = _chunk("B_c0", "beta", 2.0)
    case = _case(
        [
            {"query": "q1", "ticker": "AAPL", "chunks": [a, b]},
            {"query": "q2", "ticker": "AMZN", "chunks": [a]},
        ],
        "comparative",
    )

    assert [e["chunk_id"] for e in collect_entries(case)] == ["A_c0", "B_c0"]


@pytest.mark.parametrize("strategy", [CONTEXT_STRATEGY_ROUTE_AWARE])
def test_never_adds_evidence_beyond_full_set(strategy: str) -> None:
    entries = [_chunk(f"D_c{i}", "shared keyword", float(i)) for i in range(3)]
    case = _case([{"query": "q", "ticker": None, "chunks": entries}], "fact_lookup")

    packed = pack_case_context(
        case, required_keywords=["shared keyword"], strategy=strategy
    )

    full_ids = {e["chunk_id"] for e in collect_entries(case)}
    assert set(packed.kept_ids).issubset(full_ids)


def test_comparative_v3_keeps_two_leading_chunks_per_branch() -> None:
    case = _case(
        [
            {
                "query": "apple",
                "ticker": "AAPL",
                "chunks": [
                    _chunk("A_0", "apple primary", 3.0, "AAPL"),
                    _chunk("A_1", "apple support", 2.0, "AAPL"),
                    _chunk("A_2", "apple noise", 1.0, "AAPL"),
                ],
            },
            {
                "query": "microsoft",
                "ticker": "MSFT",
                "chunks": [
                    _chunk("M_0", "microsoft primary", 3.0, "MSFT"),
                    _chunk("M_1", "microsoft support", 2.0, "MSFT"),
                    _chunk("M_2", "microsoft noise", 1.0, "MSFT"),
                ],
            },
        ],
        "comparative",
    )

    packed = pack_case_context(
        case,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V3,
    )

    assert packed.kept_ids == ["A_0", "A_1", "M_0", "M_1"]


def test_comparative_v3_adds_fact_override_donor_below_branch_target() -> None:
    case = _case(
        [
            {
                "query": "aws",
                "ticker": "AMZN",
                "chunks": [
                    _chunk("AWS_0", "AWS narrative", 3.0, "AMZN"),
                    _chunk("AWS_1", "AWS cost discussion", 2.0, "AMZN"),
                    _chunk("AWS_2", "AWS values 107,556 128,725", 1.0, "AMZN"),
                ],
            },
            {
                "query": "cloud",
                "ticker": "MSFT",
                "chunks": [_chunk("MSFT_0", "Cloud growth", 3.0, "MSFT")],
            },
        ],
        "comparative",
    )
    case["question"] = (
        "How does Amazon's AWS segment compare to Microsoft's cloud business "
        "in terms of growth?"
    )

    packed = pack_case_context(
        case,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V3,
    )

    assert "AWS_2" in packed.kept_ids
    assert packed.uncovered_keywords == []


def test_comparative_v3_leaves_noncomparative_context_unchanged() -> None:
    case = _case(
        [
            {
                "query": "summary",
                "ticker": "AAPL",
                "chunks": [
                    _chunk("S_0", "one", 2.0),
                    _chunk("S_1", "two", 1.0),
                ],
            }
        ],
        "summary",
    )

    packed = pack_case_context(
        case,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V3,
    )

    assert packed.kept_ids == ["S_0", "S_1"]
    assert packed.dropped == []


def test_fact_overrides_do_not_change_historical_route_aware_strategy() -> None:
    case = _case(
        [
            {
                "query": "aws",
                "ticker": "AMZN",
                "chunks": [
                    _chunk("AWS_0", "AWS narrative", 3.0, "AMZN"),
                    _chunk("AWS_1", "AWS values 107,556 128,725", 1.0, "AMZN"),
                ],
            },
            {
                "query": "cloud",
                "ticker": "MSFT",
                "chunks": [_chunk("MSFT_0", "Cloud growth", 3.0, "MSFT")],
            },
        ],
        "comparative",
    )
    case["question"] = (
        "How does Amazon's AWS segment compare to Microsoft's cloud business "
        "in terms of growth?"
    )

    packed = pack_case_context(
        case,
        strategy=CONTEXT_STRATEGY_ROUTE_AWARE,
    )

    assert packed.kept_ids == ["AWS_0", "MSFT_0"]
