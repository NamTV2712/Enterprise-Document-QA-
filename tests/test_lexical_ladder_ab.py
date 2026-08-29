from scripts.diagnostics.lexical_ladder_ab import _scoped_chunks


class _Retriever:
    _all_chunks = [
        {"chunk_id": "a", "ticker": "AMZN", "section": "mdna"},
        {"chunk_id": "b", "ticker": "MSFT", "section": "mdna"},
        {"chunk_id": "c", "ticker": "AMZN", "section": "business"},
    ]


def test_scoped_chunks_applies_both_metadata_filters() -> None:
    chunks = _scoped_chunks(_Retriever(), "AMZN", "mdna")

    assert [chunk["chunk_id"] for chunk in chunks] == ["a"]
