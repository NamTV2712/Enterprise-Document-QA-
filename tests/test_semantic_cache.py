from src.retrieval.semantic_cache import SemanticCache, make_filter_key


def test_make_filter_key_uses_wildcards_for_missing_filters() -> None:
    assert make_filter_key(None, None, 5) == "*|*|5"
    assert make_filter_key("AAPL", None, 3) == "AAPL|*|3"
    assert make_filter_key(None, "risk_factors", 2) == "*|risk_factors|2"


def test_cache_hit_requires_matching_filters() -> None:
    cache = SemanticCache(similarity_threshold=0.99)
    embedding = [1.0, 0.0, 0.0]

    cache.set(
        query_embedding=embedding,
        ticker="AAPL",
        section="business",
        top_k=5,
        answer="cached answer",
        sources=[{"chunk_id": "a"}],
        model_used="test-model",
    )

    assert cache.get(embedding, ticker="AAPL", section="business", top_k=5) is not None
    assert cache.get(embedding, ticker="MSFT", section="business", top_k=5) is None
    assert cache.get(embedding, ticker="AAPL", section="risk_factors", top_k=5) is None
    assert cache.get(embedding, ticker="AAPL", section="business", top_k=3) is None


def test_similar_but_different_financial_queries_do_not_hit() -> None:
    """Revenue and net income questions are similar but not interchangeable."""
    cache = SemanticCache(similarity_threshold=0.95)
    revenue_embedding = [1.0, 0.0]
    net_income_embedding = [0.92, 0.39191835884530846]

    assert round(cache.test_similarity(revenue_embedding, net_income_embedding), 4) == 0.92

    cache.set(
        query_embedding=revenue_embedding,
        ticker="AAPL",
        section="financial_statements",
        top_k=5,
        answer="Apple revenue answer",
        sources=[{"chunk_id": "revenue"}],
        model_used="test-model",
    )

    assert (
        cache.get(
            net_income_embedding,
            ticker="AAPL",
            section="financial_statements",
            top_k=5,
        )
        is None
    )


def test_cache_entry_expires_after_ttl(monkeypatch) -> None:
    current_time = 100.0
    monkeypatch.setattr(
        "src.retrieval.semantic_cache.time.monotonic",
        lambda: current_time,
    )
    cache = SemanticCache(similarity_threshold=0.99, ttl_seconds=10)
    embedding = [1.0, 0.0]

    cache.set(embedding, None, None, 5, "answer", [], "test-model")
    assert cache.get(embedding, None, None, 5) is not None

    current_time = 111.0
    assert cache.get(embedding, None, None, 5) is None
    assert cache.get_stats()["entries"] == 0


def test_cache_evicts_least_used_entry_when_full() -> None:
    cache = SemanticCache(similarity_threshold=0.99, max_entries=2)
    first = [1.0, 0.0, 0.0]
    second = [0.0, 1.0, 0.0]
    third = [0.0, 0.0, 1.0]

    cache.set(first, "AAPL", None, 5, "first", [], "test-model")
    cache.set(second, "MSFT", None, 5, "second", [], "test-model")

    assert cache.get(first, "AAPL", None, 5) is not None

    cache.set(third, "AMZN", None, 5, "third", [], "test-model")

    assert cache.get(first, "AAPL", None, 5) is not None
    assert cache.get(second, "MSFT", None, 5) is None
    assert cache.get(third, "AMZN", None, 5) is not None


def test_clear_removes_entries_and_resets_stats() -> None:
    cache = SemanticCache(similarity_threshold=0.99)
    embedding = [1.0, 0.0]
    cache.set(embedding, None, None, 5, "answer", [], "test-model")
    assert cache.get(embedding, None, None, 5) is not None

    assert cache.clear() == 1

    stats = cache.get_stats()
    assert stats["entries"] == 0
    assert stats["total_requests"] == 0
    assert stats["cache_hits"] == 0
