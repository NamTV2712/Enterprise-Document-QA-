"""Deterministic offline spot-checks for the FY2026 corpus recovery.

These tests pin the five sections recovered for the 46/50 corpus
milestone: ``financial_statements`` for NOW, NVDA, ORCL, and PEP plus
``mdna`` for PFE. They read only the local embedded-chunk artifacts and
run a lexical BM25 ranking over each ticker's own chunks — no provider,
no embedding model, no Qdrant lock. On machines without the git-ignored
corpus the module skips like the other baseline regression.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Grounded against the rebuilt corpus: genuine statement/MD&A markers that
# only appear where real section bodies exist (never in TOC page refs).
RECOVERY_EXPECTATIONS = {
    "NOW": {
        "section": "financial_statements",
        "min_chunks": 20,
        "genuine_markers": ["consolidated balance sheets", "total assets"],
    },
    "NVDA": {
        "section": "financial_statements",
        "min_chunks": 20,
        "genuine_markers": ["consolidated balance sheets", "total assets"],
    },
    "ORCL": {
        "section": "financial_statements",
        "min_chunks": 40,
        "genuine_markers": ["consolidated balance sheets", "total assets"],
    },
    "PEP": {
        "section": "financial_statements",
        "min_chunks": 8,
        "genuine_markers": ["consolidated statements of income"],
    },
    "PFE": {
        "section": "mdna",
        "min_chunks": 40,
        "genuine_markers": ["the following md&a", "results of operations"],
    },
}

# Queries whose lexical evidence can only come from real recovered bodies.
BM25_QUERIES = {
    "NOW": ("consolidated balance sheets total assets", "financial_statements"),
    "NVDA": ("consolidated balance sheets total assets", "financial_statements"),
    "ORCL": ("consolidated balance sheets total assets", "financial_statements"),
    "PEP": ("consolidated statements of income", "financial_statements"),
    "PFE": ("results of operations gross margin revenue", "mdna"),
}

TABLE_RECOVERY_EXPECTATIONS = {
    "CVX": (33, "Consolidated Statement of Income"),
    "JPM": (6, "Consolidated statements of income"),
    "XOM": (4, "CONSOLIDATED STATEMENT OF INCOME"),
    "IBM": (32, "Consolidated Income Statement"),
}


def _load_ticker_chunks(ticker: str) -> list[dict]:
    paths = sorted((PROCESSED_DIR / ticker).glob("*_chunks_embedded.jsonl"))
    if not paths:
        return []
    records: list[dict] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _compact(text: str) -> str:
    return "".join(text.split()).lower()


@pytest.fixture(scope="module")
def ticker_chunks() -> dict[str, list[dict]]:
    if not PROCESSED_DIR.is_dir():
        pytest.skip("local corpus not available")
    loaded = {
        ticker: _load_ticker_chunks(ticker)
        for ticker in RECOVERY_EXPECTATIONS
    }
    if any(not chunks for chunks in loaded.values()):
        pytest.skip("local corpus not available")
    return loaded


@pytest.mark.parametrize("ticker", sorted(RECOVERY_EXPECTATIONS))
def test_recovered_section_has_real_content(
    ticker: str, ticker_chunks: dict[str, list[dict]]
) -> None:
    expectation = RECOVERY_EXPECTATIONS[ticker]
    section = expectation["section"]
    chunks = [
        chunk for chunk in ticker_chunks[ticker]
        if chunk.get("section") == section
    ]

    # The recovered section exists with substantial body content and every
    # chunk carries the correct ticker/section metadata.
    assert len(chunks) >= expectation["min_chunks"], (
        f"{ticker}/{section} has only {len(chunks)} chunks"
    )
    assert all(chunk.get("ticker") == ticker for chunk in chunks)

    joined = " ".join(chunk.get("text", "") for chunk in chunks)
    compact = _compact(joined)
    for marker in expectation["genuine_markers"]:
        assert _compact(marker) in compact, (
            f"{ticker}/{section} lacks genuine marker {marker!r}; "
            "recovery produced a stub instead of real section body"
        )

    if section == "mdna":
        first = chunks[0].get("text", "")
        # PFE regression: the slice must start at the real ITEM 7 body
        # heading, not the TOC page-reference block.
        assert first.upper().startswith("ITEM 7.")
        assert "GENERAL" in first[:300].upper()
        assert not re.match(r"^ITEM 7\..*OPERATIONS\s+\d+\s*\n", first), (
            "PFE mdna starts at the table-of-contents reference"
        )


@pytest.mark.parametrize("ticker", sorted(RECOVERY_EXPECTATIONS))
def test_recovered_section_is_lexically_retrievable(
    ticker: str, ticker_chunks: dict[str, list[dict]]
) -> None:
    from rank_bm25 import BM25Okapi

    query, expected_section = BM25_QUERIES[ticker]
    corpus = ticker_chunks[ticker]
    bm25 = BM25Okapi([_tokenize(c.get("text", "")) for c in corpus])
    scores = bm25.get_scores(_tokenize(query))
    top_order = sorted(range(len(corpus)), key=lambda i: -scores[i])[:10]

    hits = [
        corpus[i] for i in top_order
        if corpus[i].get("section") == expected_section
    ]
    assert hits, (
        f"{ticker}: no {expected_section} chunk in lexical top-10 for {query!r}"
    )
    # A retrieved hit must be real section body, never a TOC/reference stub.
    assert any(len(h.get("text", "")) >= 500 for h in hits), (
        f"{ticker}: retrieved {expected_section} hits are all short stubs"
    )


@pytest.mark.parametrize("ticker", sorted(TABLE_RECOVERY_EXPECTATIONS))
def test_hard_group_table_recovery_is_present_and_grounded(ticker: str) -> None:
    if not PROCESSED_DIR.is_dir():
        pytest.skip("local corpus not available")
    expected_count, required_marker = TABLE_RECOVERY_EXPECTATIONS[ticker]
    chunks = [
        chunk
        for chunk in _load_ticker_chunks(ticker)
        if chunk.get("section") == "financial_table"
    ]

    assert len(chunks) == expected_count
    assert all(chunk.get("ticker") == ticker for chunk in chunks)
    assert any(required_marker.casefold() in chunk.get("text", "").casefold() for chunk in chunks)
