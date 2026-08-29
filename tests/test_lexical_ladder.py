from src.retrieval.lexical_ladder import (
    LEXICAL_LADDER_FINGERPRINT,
    lexical_ladder_candidates,
)


def _chunk(chunk_id: str, text: str, ticker: str = "AMZN") -> dict:
    return {
        "chunk_id": chunk_id,
        "ticker": ticker,
        "section": "mdna",
        "text": text,
    }


def test_ladder_prefers_exact_phrase_over_broader_tiers() -> None:
    candidates = lexical_ladder_candidates(
        [
            _chunk("exact", "AWS - Net sales | 107,556 | 128,725"),
            _chunk("partial", "AWS operating sales growth"),
        ],
        ticker="AMZN",
        section="mdna",
        exact_phrases=("AWS net sales",),
        full_terms=("AWS", "net", "sales"),
        partial_terms=("AWS", "net", "sales"),
    )

    assert [candidate.chunk["chunk_id"] for candidate in candidates] == ["exact"]
    assert candidates[0].tier == "exact_phrase"


def test_ladder_falls_through_to_full_then_partial_terms() -> None:
    full = lexical_ladder_candidates(
        [_chunk("full", "AWS generated net sales")],
        ticker="AMZN",
        section="mdna",
        exact_phrases=("missing phrase",),
        full_terms=("AWS", "net", "sales"),
        partial_terms=("AWS", "net", "sales"),
    )
    partial = lexical_ladder_candidates(
        [_chunk("partial", "AWS sales increased")],
        ticker="AMZN",
        section="mdna",
        exact_phrases=("missing phrase",),
        full_terms=("AWS", "net", "sales"),
        partial_terms=("AWS", "net", "sales"),
    )

    assert full[0].tier == "full_terms"
    assert partial[0].tier == "partial_terms"


def test_fuzzy_is_ticker_guarded_and_last_resort() -> None:
    chunks = [_chunk("fuzzy", "AWS nett saless")]
    disabled = lexical_ladder_candidates(
        chunks,
        ticker=None,
        section="mdna",
        fuzzy_terms=("sales",),
    )
    enabled = lexical_ladder_candidates(
        chunks,
        ticker="AMZN",
        section="mdna",
        fuzzy_terms=("sales",),
    )

    assert disabled == []
    assert enabled[0].tier == "fuzzy"


def test_scope_is_applied_before_matching() -> None:
    candidates = lexical_ladder_candidates(
        [
            _chunk("amzn", "AWS net sales", "AMZN"),
            _chunk("msft", "AWS net sales", "MSFT"),
        ],
        ticker="AMZN",
        section="mdna",
        exact_phrases=("AWS net sales",),
    )

    assert [candidate.chunk["chunk_id"] for candidate in candidates] == ["amzn"]


def test_ladder_fingerprint_is_sha256() -> None:
    assert LEXICAL_LADDER_FINGERPRINT.startswith("sha256:")
    assert len(LEXICAL_LADDER_FINGERPRINT) == len("sha256:") + 64
