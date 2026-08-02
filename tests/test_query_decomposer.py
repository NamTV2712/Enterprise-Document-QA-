"""
Tests for QueryDecomposer plan validation.

These tests do not call external LLM APIs. They cover the validation guard for
LLM-generated planner output, including out-of-corpus ticker guesses.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.generation.query_decomposer import (
    INSUFFICIENT_DECOMPOSED_CONTEXT_ANSWER,
    QueryDecomposer,
    SubQuery,
)
from src.retrieval.retriever import RetrievedChunk


def _make_decomposer() -> QueryDecomposer:
    # _validate_plan does not call the generator or retriever.
    return QueryDecomposer(SimpleNamespace(generator=None, retriever=None))


def _make_chunk(chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        ticker="AMZN",
        section="business",
        filing_date="2026-02-01",
        score=0.5,
        text="Amazon context.",
        citation="AMZN 10-K, Section: Business",
    )


def _make_ticker_chunk(chunk_id: str, ticker: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        ticker=ticker,
        section="mdna",
        filing_date="2025-01-01",
        score=1.0,
        text=f"{ticker} cloud evidence.",
        citation=f"{ticker} 10-K, Section: MD&A",
    )


def _make_runnable_decomposer() -> QueryDecomposer:
    pipeline = SimpleNamespace(
        generator=SimpleNamespace(model="fake-model"),
        retriever=MagicMock(),
        query=MagicMock(),
    )
    return QueryDecomposer(pipeline)


def test_invalid_ticker_dropped() -> None:
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Disney risk factors", "ticker": "DIS", "section": "risk_factors"},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is False


def test_valid_ticker_kept() -> None:
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "MSFT cloud revenue", "ticker": "MSFT", "section": "business"},
            {"query": "MSFT gaming revenue", "ticker": "MSFT", "section": "business"},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is True
    assert len(result["sub_queries"]) == 2


def test_expanded_corpus_tickers_kept() -> None:
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Visa risk factors", "ticker": "V", "section": "risk_factors"},
            {"query": "Mastercard risk factors", "ticker": "MA", "section": "risk_factors"},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is True
    assert [sq["ticker"] for sq in result["sub_queries"]] == ["V", "MA"]


def test_mixed_valid_invalid_tickers() -> None:
    """Keep valid sub-queries while dropping invalid ticker guesses."""
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Apple revenue", "ticker": "AAPL", "section": "financial_statements"},
            {"query": "Netflix revenue", "ticker": "NFLX", "section": "financial_statements"},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is True
    assert len(result["sub_queries"]) == 1
    assert result["sub_queries"][0]["ticker"] == "AAPL"


def test_invalid_section_dropped() -> None:
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Apple something", "ticker": "AAPL", "section": "exhibits"},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is False


def test_financial_table_section_kept() -> None:
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Apple total net sales", "ticker": "AAPL", "section": "financial_table"},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is True
    assert result["sub_queries"][0]["section"] == "financial_table"


def test_null_ticker_and_section_always_valid() -> None:
    """None means search all and should not be filtered out."""
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "risk factors comparison", "ticker": None, "section": None},
        ],
    }

    result = decomposer._validate_plan(fake_plan)

    assert result["needs_decomposition"] is True
    assert len(result["sub_queries"]) == 1


def test_simple_plan_passthrough_unchanged() -> None:
    decomposer = _make_decomposer()
    fake_plan = {"needs_decomposition": False}

    result = decomposer._validate_plan(fake_plan)

    assert result == {"needs_decomposition": False}


def test_decomposed_query_with_too_little_context_returns_fallback(monkeypatch) -> None:
    decomposer = _make_runnable_decomposer()
    sub_query = {"query": "Amazon business segments", "ticker": "AMZN", "section": "business"}

    monkeypatch.setattr(
        decomposer,
        "_plan",
        lambda question: {"needs_decomposition": True, "sub_queries": [sub_query]},
    )
    monkeypatch.setattr(
        decomposer,
        "_execute_parallel",
        lambda sub_queries, top_k: [
            SimpleNamespace(**sub_query, retrieved_chunks=[_make_chunk("chunk-1")])
        ],
    )
    synthesize = MagicMock(return_value="hallucinated answer")
    monkeypatch.setattr(decomposer, "_synthesize", synthesize)

    result = decomposer.run("What are Amazon's business segments?")

    assert result.answer == INSUFFICIENT_DECOMPOSED_CONTEXT_ANSWER
    assert result.was_decomposed is True
    assert len(result.all_chunks) == 1
    synthesize.assert_not_called()


def test_decomposed_query_with_enough_context_synthesizes(monkeypatch) -> None:
    decomposer = _make_runnable_decomposer()
    sub_query = {"query": "Amazon business segments", "ticker": "AMZN", "section": "business"}

    monkeypatch.setattr(
        decomposer,
        "_plan",
        lambda question: {"needs_decomposition": True, "sub_queries": [sub_query]},
    )
    monkeypatch.setattr(
        decomposer,
        "_execute_parallel",
        lambda sub_queries, top_k: [
            SimpleNamespace(
                **sub_query,
                retrieved_chunks=[_make_chunk("chunk-1"), _make_chunk("chunk-2")],
            )
        ],
    )
    synthesize = MagicMock(return_value="grounded synthesized answer")
    monkeypatch.setattr(decomposer, "_synthesize", synthesize)

    result = decomposer.run("What are Amazon's business segments?")

    assert result.answer == "grounded synthesized answer"
    assert len(result.all_chunks) == 2
    synthesize.assert_called_once()


def test_synthesis_exception_does_not_leak_to_public_response() -> None:
    """Non-retryable synthesis failures must return a stable public message."""
    generator = MagicMock()
    generator.model = "fake-model"
    generator.client.chat.completions.create.side_effect = RuntimeError(
        "Connection failed: api_key=sk-secret-abc123 at /internal/models/path"
    )
    decomposer = QueryDecomposer(
        SimpleNamespace(generator=generator, retriever=MagicMock())
    )

    answer = decomposer._synthesize(
        "What are Amazon's risks?",
        [_make_chunk("chunk-1")],
    )

    assert "sk-secret-abc123" not in answer
    assert "/internal/models/path" not in answer
    assert "RuntimeError" not in answer
    assert answer == (
        "I encountered an error while synthesizing the answer from the "
        "retrieved sources. Please try rephrasing your question."
    )


def test_comparative_query_with_all_evidence_from_one_company_falls_back(
    monkeypatch,
) -> None:
    """A multi-company comparison must not synthesize one-sided evidence."""
    decomposer = _make_runnable_decomposer()
    planned_sub_queries = [
        {"query": "Apple cloud revenue", "ticker": "AAPL", "section": "mdna"},
        {"query": "Microsoft cloud revenue", "ticker": "MSFT", "section": "mdna"},
    ]
    executed_sub_queries = [
        SubQuery(
            **planned_sub_queries[0],
            retrieved_chunks=[_make_ticker_chunk("AAPL_0", "AAPL")],
        ),
        SubQuery(
            **planned_sub_queries[1],
            retrieved_chunks=[_make_ticker_chunk("AAPL_1", "AAPL")],
        ),
    ]
    monkeypatch.setattr(
        decomposer,
        "_plan",
        lambda question: {
            "needs_decomposition": True,
            "sub_queries": planned_sub_queries,
        },
    )
    monkeypatch.setattr(
        decomposer,
        "_execute_parallel",
        lambda sub_queries, top_k: executed_sub_queries,
    )
    synthesize = MagicMock(return_value="one-sided comparison")
    monkeypatch.setattr(decomposer, "_synthesize", synthesize)

    result = decomposer.run(
        "Compare Apple and Microsoft's cloud revenue",
        top_k=3,
    )

    synthesize.assert_not_called()
    assert result.answer == INSUFFICIENT_DECOMPOSED_CONTEXT_ANSWER
    assert result.was_decomposed is True
    assert {chunk.ticker for chunk in result.all_chunks} == {"AAPL"}


def test_comparative_query_with_per_company_evidence_still_synthesizes(
    monkeypatch,
) -> None:
    """Valid multi-company evidence must continue to reach synthesis."""
    decomposer = _make_runnable_decomposer()
    planned_sub_queries = [
        {"query": "Apple cloud revenue", "ticker": "AAPL", "section": "mdna"},
        {"query": "Microsoft cloud revenue", "ticker": "MSFT", "section": "mdna"},
    ]
    executed_sub_queries = [
        SubQuery(
            **planned_sub_queries[0],
            retrieved_chunks=[_make_ticker_chunk("AAPL_0", "AAPL")],
        ),
        SubQuery(
            **planned_sub_queries[1],
            retrieved_chunks=[_make_ticker_chunk("MSFT_0", "MSFT")],
        ),
    ]
    monkeypatch.setattr(
        decomposer,
        "_plan",
        lambda question: {
            "needs_decomposition": True,
            "sub_queries": planned_sub_queries,
        },
    )
    monkeypatch.setattr(
        decomposer,
        "_execute_parallel",
        lambda sub_queries, top_k: executed_sub_queries,
    )
    synthesize = MagicMock(return_value="grounded comparison")
    monkeypatch.setattr(decomposer, "_synthesize", synthesize)

    result = decomposer.run(
        "Compare Apple and Microsoft's cloud revenue",
        top_k=3,
    )

    synthesize.assert_called_once()
    assert result.answer == "grounded comparison"
    assert result.was_decomposed is True
    assert {chunk.ticker for chunk in result.all_chunks} == {"AAPL", "MSFT"}
