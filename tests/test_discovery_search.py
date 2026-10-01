"""API-004 discovery search: domain, snapshot lifecycle, route, and safety tests.

Hermetic: discovery scores with a real BM25 index built over a tiny in-memory
fixture corpus, so the tests exercise the production scoring path without
loading a model, calling a provider, or touching the network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from rank_bm25 import BM25Okapi

from src.api import app as app_module
from src.api.discovery import (
    CANDIDATE_CEILING,
    COUNT_SCOPE_BOUNDED,
    COUNT_SCOPE_EMPTY,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MAX_QUERY_LENGTH,
    DiscoveryError,
    DiscoveryScope,
    DiscoveryService,
    DiscoverySnapshotStore,
    build_snippet,
    discovery_query_terms,
    discovery_scope_documents,
    normalize_query,
    rank_chunks,
    validate_grouping,
    validate_mode,
    validate_page,
)
from src.retrieval.hybrid_retriever import _tokenize


NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


FIXTURE_CHUNKS = [
    {
        "chunk_id": "AAPL-c1",
        "ticker": "AAPL",
        "accession_number": "0000320193-25-000079",
        "section": "financial_statements",
        "filing_date": "2025-10-31",
        "report_date": "2025-09-27",
        "chunk_index": 0,
        "text": "Total net sales revenue was 391,035 million dollars in fiscal 2024 for Apple.",
    },
    {
        "chunk_id": "AAPL-c2",
        "ticker": "AAPL",
        "accession_number": "0000320193-25-000079",
        "section": "risk_factors",
        "filing_date": "2025-10-31",
        "report_date": "2025-09-27",
        "chunk_index": 1,
        "text": "Apple faces competition risks; revenue could decline in consumer markets.",
    },
    {
        "chunk_id": "MSFT-c1",
        "ticker": "MSFT",
        "accession_number": "0000789019-24-000095",
        "section": "mdna",
        "filing_date": "2024-09-30",
        "report_date": "2024-06-30",
        "chunk_index": 0,
        "text": "Microsoft Cloud revenue increased and Azure revenue grew in fiscal 2024.",
    },
    {
        "chunk_id": "JPM-c1",
        "ticker": "JPM",
        "accession_number": "0000019617-23-000120",
        "section": "business",
        "filing_date": "2023-02-21",
        "report_date": None,
        "chunk_index": 0,
        "text": "Doanh thu của ngân hàng tăng mạnh trong năm tài chính.",
    },
]

AAPL_DOCUMENT_ID = "AAPL:0000320193-25-000079"
MSFT_DOCUMENT_ID = "MSFT:0000789019-24-000095"


def _document_id_of(chunk: dict) -> str:
    """Use the application's own document identity so the integration matches."""
    return app_module._document_id(chunk)


def _catalog_rows(chunks: list[dict]) -> list[dict]:
    rows: dict[str, dict] = {}
    for chunk in chunks:
        document_id = _document_id_of(chunk)
        row = rows.setdefault(
            document_id,
            {
                "document_id": document_id,
                "ticker": chunk.get("ticker"),
                "filing_date": chunk.get("filing_date"),
                "report_date": chunk.get("report_date"),
                "accession_number": chunk.get("accession_number"),
                "sections": set(),
                "chunk_count": 0,
                "source_url": None,
            },
        )
        if chunk.get("section"):
            row["sections"].add(chunk["section"])
        row["chunk_count"] += 1
    return [
        {**row, "sections": sorted(row["sections"])}
        for row in sorted(rows.values(), key=lambda item: item["document_id"])
    ]


class FakeRetriever:
    """A retriever double with a real tokenizer and a real BM25 index."""

    def __init__(self, chunks: list[dict]) -> None:
        self._all_chunks = chunks
        self.bm25 = BM25Okapi([_tokenize(chunk["text"]) for chunk in chunks])
        self.embedder = MagicMock()
        self.cross_encoder = MagicMock()
        self._model_lock = MagicMock()

    def tokenize_query(self, text: str) -> list[str]:
        return _tokenize(text)

    def bm25_scores(self, tokens: list[str]) -> list[float]:
        return [float(score) for score in self.bm25.get_scores(tokens)]

    def bm25_terms_present(self, tokens: list[str]) -> list[bool]:
        wanted = set(tokens)
        return [
            any(term in document_terms for term in wanted)
            for document_terms in self.bm25.doc_freqs
        ]


def _service(
    *,
    chunks: list[dict] | None = None,
    store: DiscoverySnapshotStore | None = None,
) -> DiscoveryService:
    payload_chunks = FIXTURE_CHUNKS if chunks is None else chunks
    retriever = FakeRetriever(payload_chunks)
    return DiscoveryService(
        chunks=lambda: retriever._all_chunks,
        catalog_rows=lambda: _catalog_rows(payload_chunks),
        tokenize=retriever.tokenize_query,
        score=retriever.bm25_scores,
        document_id_of=_document_id_of,
        snapshot_store=store,
    )


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    app_module.limiter.reset()
    yield
    app_module.limiter.reset()


@pytest.fixture
def client():
    """Inject the fixture corpus and discovery service without a lifespan."""
    retriever = FakeRetriever(FIXTURE_CHUNKS)
    pipeline = MagicMock()
    pipeline.retriever = retriever
    pipeline.memory.get_stats.return_value = {"active_sessions": 0, "total_turns": 0}
    app_module._state.clear()
    app_module._state["pipeline"] = pipeline
    app_module._state["store"] = MagicMock()
    app_module._state["document_rows"] = _catalog_rows(FIXTURE_CHUNKS)
    test_client = TestClient(app_module.app)
    yield test_client
    app_module._state.clear()


# --- Query normalization ---------------------------------------------------


def test_normalization_is_deterministic_and_bounded() -> None:
    assert normalize_query("  Apple   Revenue 2024 ") == "apple revenue 2024"
    assert normalize_query("Doanh thu") == "doanh thu"
    with pytest.raises(DiscoveryError):
        normalize_query("a")
    with pytest.raises(DiscoveryError):
        normalize_query("   ")
    with pytest.raises(DiscoveryError):
        normalize_query("x" * (MAX_QUERY_LENGTH + 1))


def test_query_terms_keep_unicode_words_and_never_drop_capitals() -> None:
    assert discovery_query_terms("Doanh thu tăng mạnh") == ("doanh", "thu", "tăng", "mạnh")
    # A caller that skipped normalization must not lose a leading capital.
    assert discovery_query_terms("Apple revenue") == ("apple", "revenue")
    assert discovery_query_terms("revenue revenue 2024") == ("revenue", "2024")


def test_mode_grouping_and_page_validation() -> None:
    assert validate_mode("keyword") == "keyword"
    with pytest.raises(DiscoveryError):
        validate_mode("natural")
    assert validate_grouping("document") == "document"
    with pytest.raises(DiscoveryError):
        validate_grouping("ticker")
    assert validate_page(1, DEFAULT_PAGE_SIZE) == (1, DEFAULT_PAGE_SIZE)
    with pytest.raises(DiscoveryError):
        validate_page(0, DEFAULT_PAGE_SIZE)
    with pytest.raises(DiscoveryError):
        validate_page(1, MAX_PAGE_SIZE + 1)


# --- Snippets --------------------------------------------------------------


def test_snippet_windows_around_the_first_match_and_reports_ranges() -> None:
    text = (
        "prefix words before the match " * 8
        + "revenue increased 23 percent in 2024 "
        + "tail words after the match " * 30
    )
    snippet = build_snippet(text, ("revenue", "2024"))

    assert snippet.truncated is True
    assert snippet.text.startswith("…")
    assert snippet.text.endswith("…")
    assert "revenue increased 23 percent in 2024" in snippet.text
    for start, end in snippet.ranges:
        assert 0 <= start < end <= len(snippet.text)
        assert snippet.text[start:end].casefold() in {"revenue", "2024"}


def test_snippet_is_bounded_and_handles_empty_or_unmatched_text() -> None:
    long_text = "body text " * 200
    snippet = build_snippet(long_text, ("body",))
    assert len(snippet.text) <= 242  # window plus the two ellipsis markers

    empty = build_snippet("", ("term",))
    assert empty.text == "" and empty.ranges == ()

    unmatched = build_snippet("completely unrelated words", ("absent",))
    assert unmatched.ranges == ()
    assert unmatched.text.startswith("completely")


# --- Ranking ---------------------------------------------------------------


def test_ranking_is_deterministic_and_preserves_identity() -> None:
    retriever = FakeRetriever(FIXTURE_CHUNKS)
    result = rank_chunks(
        FIXTURE_CHUNKS,
        retriever.tokenize_query("revenue"),
        discovery_query_terms("revenue"),
        retriever.bm25_scores,
        allowed_documents=None,
        document_id_of=_document_id_of,
    )

    chunk_ids = [hit.chunk_id for hit in result.hits]
    assert chunk_ids  # the fixture contains the term
    assert all(hit.score > 0 for hit in result.hits)
    assert all(hit.document_id != hit.chunk_id for hit in result.hits)
    # Ranking is by score, and repeating the call returns the identical order.
    assert [hit.score for hit in result.hits] == sorted(
        (hit.score for hit in result.hits), reverse=True
    )
    # Repeating the same call returns the identical order and scores.
    repeat = rank_chunks(
        FIXTURE_CHUNKS,
        retriever.tokenize_query("revenue"),
        discovery_query_terms("revenue"),
        retriever.bm25_scores,
        allowed_documents=None,
        document_id_of=_document_id_of,
    )
    assert repeat.hits == result.hits


def test_ranking_filters_to_the_scope_documents_and_groups_by_document() -> None:
    service = _service()
    snapshot = service.search(query="revenue", ticker="AAPL")

    assert snapshot.scope_documents == 1
    assert snapshot.result.matched_documents == 1
    assert all(hit.document_id.startswith("AAPL") for hit in snapshot.result.hits)
    group = snapshot.result.groups[0]
    assert group.document_id.startswith("AAPL")
    assert group.hit_count == 2
    assert group.best_score == max(hit.score for hit in group.hits)
    assert list(group.sections) == ["financial_statements", "risk_factors"]


def test_ranking_returns_no_hits_for_an_absent_term() -> None:
    service = _service()
    snapshot = service.search(query="zzzznotpresent")

    assert snapshot.result.hits == ()
    assert snapshot.result.groups == ()
    assert snapshot.result.matched_documents == 0
    payload = snapshot.as_payload(1, DEFAULT_PAGE_SIZE)
    assert payload["total"] == 0
    assert payload["items"] == []
    assert payload["scope"]["count_scope"] == COUNT_SCOPE_EMPTY


def test_ranking_applies_the_candidate_ceiling() -> None:
    # The term appears in enough chunks to be a real match, and the ceiling is
    # what limits the returned page rather than the score distribution.
    chunks = [
        {
            "chunk_id": f"FILL-c{index}",
            "ticker": "FILL",
            "section": "business",
            "filing_date": "2024-01-01",
            "report_date": None,
            "chunk_index": index,
            "text": f"searched word with {word} filler",
        }
        for index, word in enumerate(
            ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
        )
    ]
    retriever = FakeRetriever(chunks)
    result = rank_chunks(
        chunks,
        retriever.tokenize_query("searched"),
        discovery_query_terms("searched"),
        retriever.bm25_scores,
        present_for=retriever.bm25_terms_present,
        allowed_documents=None,
        document_id_of=_document_id_of,
        ceiling=3,
    )

    assert len(result.hits) == 3
    assert result.matched_chunks == 3
    assert result.limited_by_ceiling is True
    assert CANDIDATE_CEILING >= 3


def test_a_term_present_in_every_chunk_still_matches_with_a_zero_score() -> None:
    # A common term gets a non-positive inverse document frequency, so BM25
    # scores it zero; it must still be found, and zero must not read as absent.
    chunks = [
        {
            "chunk_id": f"SAME-c{index}",
            "ticker": "SAME",
            "section": "business",
            "filing_date": "2024-01-01",
            "report_date": None,
            "chunk_index": index,
            "text": "revenue appears in every single chunk of this fixture",
        }
        for index in range(4)
    ]
    retriever = FakeRetriever(chunks)
    result = rank_chunks(
        chunks,
        retriever.tokenize_query("revenue"),
        discovery_query_terms("revenue"),
        retriever.bm25_scores,
        present_for=retriever.bm25_terms_present,
        allowed_documents=None,
        document_id_of=_document_id_of,
    )

    assert len(result.hits) == 4
    assert all(hit.score <= 0 for hit in result.hits)
    assert all(hit.snippet.ranges for hit in result.hits)


# --- Snapshot lifecycle ----------------------------------------------------


def _clock(start: datetime):
    current = {"now": start}

    def read() -> datetime:
        return current["now"]

    def advance(**kwargs) -> None:
        current["now"] = current["now"] + timedelta(**kwargs)

    return read, advance


def test_snapshot_store_keeps_a_stable_result_set_across_pages() -> None:
    service = _service()
    snapshot = service.search(query="revenue", page_size=1)

    assert len(snapshot.result.groups) == 2  # AAPL and MSFT both match
    first_page = snapshot.as_payload(1, 1)
    second_page = snapshot.as_payload(2, 1)

    assert first_page["search_id"] == second_page["search_id"]
    assert first_page["total"] == second_page["total"] == 2
    assert first_page["items"][0] != second_page["items"][0]
    assert first_page["items"][0] == snapshot.as_payload(1, 1)["items"][0]
    assert snapshot.as_payload(99, 1)["items"] == []


def test_snapshot_ids_are_opaque_tokens() -> None:
    service = _service()
    first = service.search(query="revenue")
    second = service.search(query="revenue")

    assert first.search_id.startswith("search-")
    assert len(first.search_id) == len("search-") + 16
    assert first.search_id != second.search_id
    # An id can never be a filesystem path or another route segment.
    for search_id in (first.search_id, second.search_id):
        assert service.snapshots.status(search_id) == "live"
    assert service.snapshots.status("../etc/passwd") == "unknown"
    assert service.snapshots.get("search-../../etc") is None


def test_snapshot_expiry_is_clock_driven_and_never_extended_by_a_read() -> None:
    read_clock, advance = _clock(NOW)
    store = DiscoverySnapshotStore(ttl_seconds=60, clock=read_clock)
    service = _service(store=store)
    snapshot = service.search(query="revenue")

    assert store.status(snapshot.search_id) == "live"
    assert snapshot.expires_at == NOW + timedelta(seconds=60)

    advance(seconds=30)
    assert store.status(snapshot.search_id) == "live"
    assert store.get(snapshot.search_id) is not None
    # A read after half the TTL must not push the expiry out.
    assert store.get(snapshot.search_id).expires_at == NOW + timedelta(seconds=60)

    advance(seconds=31)
    assert store.status(snapshot.search_id) == "expired"
    assert store.get(snapshot.search_id) is None
    # The rejected id reads as unknown afterwards.
    assert store.status(snapshot.search_id) == "unknown"


def test_snapshot_store_is_bounded_and_evicts_the_earliest_expiring_entry() -> None:
    read_clock, advance = _clock(NOW)
    store = DiscoverySnapshotStore(ttl_seconds=600, max_entries=3, clock=read_clock)
    service = _service(store=store)

    first = service.search(query="revenue")
    advance(seconds=1)
    second = service.search(query="revenue")
    advance(seconds=1)
    third = service.search(query="revenue")
    advance(seconds=1)
    fourth = service.search(query="revenue")

    assert store.count() == 3
    assert store.status(first.search_id) == "unknown"
    for kept in (second, third, fourth):
        assert store.status(kept.search_id) == "live"


# --- Endpoints -------------------------------------------------------------


def test_search_endpoint_returns_a_truthful_snapshot(client) -> None:
    response = client.post("/search", json={"query": "revenue", "ticker": "AAPL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["search_id"].startswith("search-")
    assert payload["query"] == {
        "text": "revenue",
        "normalized": "revenue",
        "mode": "keyword",
    }
    assert payload["engine"]["key"] == "bm25_lexical"
    assert "not a confidence" in payload["engine"]["definition"]
    assert payload["grouping"]["group_by"] == "document"
    assert payload["scope"]["ticker"] == "AAPL"
    assert payload["scope"]["documents"] == 1
    assert payload["scope"]["count_scope"] == COUNT_SCOPE_BOUNDED
    assert payload["scope"]["candidate_ceiling"] == CANDIDATE_CEILING
    assert payload["scope"]["limited_by_ceiling"] is False
    assert payload["total"] == len(payload["items"])
    assert payload["page"] == 1 and payload["page_size"] == DEFAULT_PAGE_SIZE
    assert payload["ttl_seconds"] == 900
    assert payload["created_at"].endswith("Z") and payload["expires_at"].endswith("Z")
    assert [facet["dimension"] for facet in payload["facets"]] == ["company", "year", "section"]

    item = payload["items"][0]
    assert item["document_id"].startswith("AAPL")
    hit = item["hits"][0]
    assert hit["chunk_id"].startswith("AAPL-c")
    assert hit["score"] > 0
    assert hit["snippet"]["text"]
    assert hit["snippet"]["ranges"]


def test_snapshot_endpoint_pages_a_stored_search_and_rejects_bad_ids(client) -> None:
    created = client.post("/search", json={"query": "revenue", "page_size": 1}).json()
    search_id = created["search_id"]

    first = client.get(f"/search/{search_id}", params={"page": 1, "page_size": 1})
    second = client.get(f"/search/{search_id}", params={"page": 2, "page_size": 1})
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["total"] == second.json()["total"]
    assert first.json()["items"] != second.json()["items"]
    assert first.json()["scope"] == created["scope"]

    assert client.get("/search/search-0000000000000000").status_code == 404
    assert client.get("/search/not-a-snapshot-id").status_code == 404
    assert client.get(f"/search/{search_id}", params={"page_size": 100}).status_code == 422


def test_expired_snapshot_is_reported_as_gone(client) -> None:
    read_clock, advance = _clock(NOW)
    retriever = FakeRetriever(FIXTURE_CHUNKS)
    app_module._state["discovery"] = DiscoveryService(
        chunks=lambda: retriever._all_chunks,
        catalog_rows=lambda: _catalog_rows(FIXTURE_CHUNKS),
        tokenize=retriever.tokenize_query,
        score=retriever.bm25_scores,
        document_id_of=_document_id_of,
        snapshot_store=DiscoverySnapshotStore(ttl_seconds=60, clock=read_clock),
    )

    created = client.post("/search", json={"query": "revenue"}).json()
    assert client.get(f"/search/{created['search_id']}").status_code == 200

    advance(seconds=61)
    expired = client.get(f"/search/{created['search_id']}")

    assert expired.status_code == 410
    assert "expired" in expired.json()["detail"].casefold()
    # The same id now reads as unknown, which is the truthful later state.
    assert client.get(f"/search/{created['search_id']}").status_code == 404


def test_search_validation_follows_the_existing_api_style(client) -> None:
    assert client.post("/search", json={"query": "a"}).status_code == 422
    assert client.post("/search", json={"query": "x" * (MAX_QUERY_LENGTH + 1)}).status_code == 422
    assert client.post("/search", json={"query": "revenue", "mode": "natural"}).status_code == 422
    assert client.post("/search", json={"query": "revenue", "group_by": "ticker"}).status_code == 422
    assert client.post("/search", json={"query": "revenue", "page": 0}).status_code == 422
    assert client.post("/search", json={"query": "revenue", "page_size": 51}).status_code == 422
    assert client.post("/search", json={"query": "revenue", "year": 1200}).status_code == 422
    assert client.post("/search", json={"query": "revenue", "ticker": "aapl"}).status_code == 422
    assert client.post("/search", json={}).status_code == 422


def test_empty_result_is_not_an_error(client) -> None:
    response = client.post("/search", json={"query": "zzzznotpresent"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["scope"]["count_scope"] == COUNT_SCOPE_EMPTY
    assert payload["scope"]["matched_chunks"] == 0
    # An unknown ticker scope is a truthful empty scope, not a fabricated row.
    empty_scope = client.post("/search", json={"query": "revenue", "ticker": "NVDA"}).json()
    assert empty_scope["items"] == []
    assert empty_scope["scope"]["documents"] == 0


def test_chunk_grouping_returns_flat_hits(client) -> None:
    response = client.post("/search", json={"query": "revenue", "group_by": "chunk"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["grouping"]["group_by"] == "chunk"
    assert payload["grouping"]["hit_count"] == payload["total"]
    assert "snippet" in payload["items"][0]
    assert payload["grouping"]["group_count"] >= 1


def test_discovery_is_provider_free(client) -> None:
    retriever = app_module._state["pipeline"].retriever
    response = client.post("/search", json={"query": "revenue"})

    assert response.status_code == 200
    # Only the prebuilt BM25 index was read: no embedding, no cross-encoder,
    # no generator, no store access.
    retriever.embedder.assert_not_called()
    retriever.embedder.embed_query.assert_not_called()
    retriever.cross_encoder.assert_not_called()
    retriever._model_lock.assert_not_called()
    app_module._state["pipeline"].generator.assert_not_called()


def test_discovery_scope_agrees_with_the_api003_catalog(client) -> None:
    for scope in ({}, {"ticker": "AAPL"}, {"section": "risk_factors"}, {"year": 2024}):
        search_response = client.post("/search", json={"query": "revenue", **scope})
        facets_response = client.get("/documents/facets", params=scope)

        assert search_response.status_code == 200 and facets_response.status_code == 200
        search_scope = search_response.json()["scope"]
        catalog_scope = facets_response.json()["scope"]
        assert search_scope["documents"] == catalog_scope["documents"]
        assert search_scope["ticker"] == catalog_scope["ticker"]
        assert search_scope["section"] == catalog_scope["section"]
        assert search_scope["year"] == catalog_scope["year"]
        # The facet payload is API-003's own aggregation, not a copy.
        assert [
            (facet["dimension"], facet["availability"])
            for facet in search_response.json()["facets"]
        ] == [
            (facet["dimension"], facet["availability"])
            for facet in facets_response.json()["facets"]
        ]


def test_search_scope_documents_helper_uses_catalog_filters() -> None:
    rows = _catalog_rows(FIXTURE_CHUNKS)
    scoped = discovery_scope_documents(rows, DiscoveryScope(ticker="AAPL"))
    assert [row["document_id"] for row in scoped] == [AAPL_DOCUMENT_ID]
    # The filing year is the year of the recorded filing date, as in API-003.
    assert [row["document_id"] for row in discovery_scope_documents(rows, DiscoveryScope(year=2024))] == [
        MSFT_DOCUMENT_ID
    ]
    assert [row["document_id"] for row in discovery_scope_documents(rows, DiscoveryScope(year=2025))] == [
        AAPL_DOCUMENT_ID
    ]
    assert len(discovery_scope_documents(rows, DiscoveryScope())) == 3


def test_discovery_responses_never_expose_private_workspace_data(client) -> None:
    response = client.post("/search", json={"query": "revenue"})
    encoded = response.text.casefold()

    for forbidden in ("conversation", "session_id", "workspace_mode", "token", "api_key", "sqlite"):
        assert forbidden not in encoded, f"discovery leaked {forbidden}"


def test_search_rate_limit_is_enforced_and_reports_client_rate_limit(client) -> None:
    body = {"query": "revenue"}
    for _ in range(30):
        assert client.post("/search", json=body).status_code == 200

    blocked = client.post("/search", json=body)

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "client_rate_limited"


def test_search_routes_are_public_and_read_only(client) -> None:
    # No bearer token or loopback requirement: discovery is the plan's public
    # read class, and it never mutates corpus, index, or workspace state.
    assert client.post("/search", json={"query": "revenue"}).status_code == 200
    assert client.get("/search/search-0000000000000000").status_code == 404
