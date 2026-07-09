"""
Tests for QueryDecomposer plan validation.

These tests do not call external LLM APIs. They cover the validation guard for
LLM-generated planner output, including the real out-of-corpus ticker leak seen
with NVDA.
"""

from types import SimpleNamespace

from src.generation.query_decomposer import QueryDecomposer


def _make_decomposer() -> QueryDecomposer:
    # _validate_plan does not call the generator or retriever.
    return QueryDecomposer(SimpleNamespace(generator=None, retriever=None))


def test_invalid_ticker_dropped() -> None:
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Nvidia risk factors", "ticker": "NVDA", "section": "risk_factors"},
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


def test_mixed_valid_invalid_tickers() -> None:
    """Keep valid sub-queries while dropping invalid ticker guesses."""
    decomposer = _make_decomposer()
    fake_plan = {
        "needs_decomposition": True,
        "sub_queries": [
            {"query": "Apple revenue", "ticker": "AAPL", "section": "financial_statements"},
            {"query": "Tesla revenue", "ticker": "TSLA", "section": "financial_statements"},
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
