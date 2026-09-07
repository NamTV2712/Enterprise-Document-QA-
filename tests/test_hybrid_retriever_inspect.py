from types import SimpleNamespace

import src.retrieval.hybrid_retriever as hybrid_module
from src.retrieval.hybrid_retriever import HybridRetriever


def _retriever() -> HybridRetriever:
    chunks = [
        {
            "chunk_id": "c1",
            "ticker": "AAPL",
            "section": "financial_table",
            "filing_date": "2025-10-31",
            "text": "Apple total revenue was 100 billion.",
        },
        {
            "chunk_id": "c2",
            "ticker": "AAPL",
            "section": "financial_table",
            "filing_date": "2025-10-31",
            "text": "Apple services revenue was 30 billion.",
        },
    ]
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever._all_chunks = chunks
    retriever._chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    retriever._chunk_index_map = {"c1": 0, "c2": 1}
    retriever._chunks_by_ticker = {"AAPL": chunks}
    retriever._chunks_by_section = {"financial_table": chunks}
    retriever._chunks_by_ticker_section = {("AAPL", "financial_table"): chunks}
    retriever.bm25 = SimpleNamespace(get_scores=lambda _tokens: [0.9, 0.2])
    retriever.store = SimpleNamespace(
        search=lambda **_kwargs: [{"chunk_id": "c2", "score": 0.88}]
    )
    retriever.embedder = SimpleNamespace(model_name="test-embedding", embed_query=lambda _query: [0.1])
    retriever.cross_encoder_model = "test-reranker"
    retriever.cross_encoder = SimpleNamespace(
        predict=lambda pairs, batch_size: [
            0.9 if "services" in text else 0.4
            for _query, text in pairs
        ]
    )
    retriever._model_lock = __import__("threading").Lock()
    return retriever


def test_inspect_preserves_stage_scores_and_final_ranks(monkeypatch) -> None:
    monkeypatch.setattr(hybrid_module, "lexical_ladder_candidates", lambda *_args, **_kwargs: [])
    trace = _retriever().inspect(
        "What was Apple's revenue?",
        top_k=1,
        candidate_pool=10,
        preset="hybrid_rerank",
    )

    assert trace["models"]["embedding"] == "test-embedding"
    assert trace["stages"][-1]["skipped"] is False
    assert trace["selected_chunk_ids"] == ["c2"]
    c1 = next(candidate for candidate in trace["candidates"] if candidate["chunk_id"] == "c1")
    c2 = next(candidate for candidate in trace["candidates"] if candidate["chunk_id"] == "c2")
    assert c1["bm25_rank"] == 1
    assert c2["dense_score"] == 0.88
    assert c2["final_rank"] == 1
    assert c2["selected"] is True


def test_inspect_non_reranked_preset_does_not_call_cross_encoder(monkeypatch) -> None:
    monkeypatch.setattr(hybrid_module, "lexical_ladder_candidates", lambda *_args, **_kwargs: [])
    retriever = _retriever()
    retriever.cross_encoder.predict = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("cross encoder should be skipped")
    )

    trace = retriever.inspect("What was Apple's revenue?", preset="bm25")

    assert trace["selected_chunk_ids"] == ["c1", "c2"]
    assert trace["stages"][-1]["skipped"] is True
