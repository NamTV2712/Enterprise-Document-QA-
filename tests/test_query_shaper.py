from src.retrieval.query_shaper import (
    QUERY_SHAPER_FINGERPRINT,
    QUERY_SHAPER_VERSION,
    shape_retrieval_query,
)


def test_aws_trend_query_gets_filing_native_terms() -> None:
    shaped = shape_retrieval_query("Amazon AWS growth")

    assert shaped.exact_phrases == ("AWS net sales",)
    assert shaped.full_terms == ("AWS", "net", "sales")
    assert shaped.partial_terms == ("AWS", "net", "sales")
    assert shaped.fuzzy_terms == ("sales",)
    assert all(term in shaped.retrieval_query for term in ("AWS", "net sales", "2025", "2024"))


def test_explicit_years_are_preserved_without_inventing_more_years() -> None:
    shaped = shape_retrieval_query("Amazon AWS net sales change from 2024 to 2025")

    assert "2023" not in shaped.retrieval_query
    assert shaped.retrieval_query.endswith("AWS net sales")


def test_microsoft_cloud_trend_gets_aggregate_revenue_terms() -> None:
    shaped = shape_retrieval_query("Microsoft cloud business growth")

    assert shaped.exact_phrases == ("Microsoft Cloud revenue",)
    assert shaped.full_terms == ("Microsoft", "Cloud", "revenue")
    assert shaped.partial_terms == ("Microsoft", "Cloud", "revenue")
    assert shaped.fuzzy_terms == ("revenue",)
    assert all(
        term in shaped.retrieval_query
        for term in ("Microsoft Cloud revenue", "2025", "2024")
    )


def test_microsoft_cloud_fact_lookup_is_not_treated_as_a_trend() -> None:
    shaped = shape_retrieval_query("What was Microsoft's cloud revenue in 2025?")

    assert shaped.retrieval_query == "What was Microsoft's cloud revenue in 2025?"
    assert shaped.exact_phrases == ()


def test_microsoft_cloud_comparison_gets_aggregate_revenue_terms() -> None:
    shaped = shape_retrieval_query("Microsoft cloud and Azure revenue")

    assert shaped.exact_phrases == ("Microsoft Cloud revenue",)
    assert shaped.full_terms == ("Microsoft", "Cloud", "revenue")
    assert shaped.partial_terms == ("Microsoft", "Cloud", "revenue")
    assert shaped.fuzzy_terms == ("revenue",)
    assert "Microsoft Cloud revenue" in shaped.retrieval_query
    assert "2025" not in shaped.retrieval_query
    assert "2024" not in shaped.retrieval_query


def test_unrelated_query_is_byte_preserving() -> None:
    query = "What are Apple's competition risks?"
    shaped = shape_retrieval_query(query)

    assert shaped.retrieval_query == query
    assert shaped.exact_phrases == ()
    assert shaped.full_terms == ()
    assert shaped.partial_terms == ()
    assert shaped.fuzzy_terms == ()


def test_fingerprint_is_versioned_and_sha256() -> None:
    assert QUERY_SHAPER_VERSION == 4
    assert QUERY_SHAPER_FINGERPRINT.startswith("sha256:")
    assert len(QUERY_SHAPER_FINGERPRINT) == len("sha256:") + 64
