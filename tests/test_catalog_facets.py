"""API-003 catalog facets and statistics: aggregation, scope, and contract tests.

Hermetic: the catalog is injected through the application state and no model,
provider, store, or network path is initialized or called.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api import app as app_module
from src.api.catalog import (
    DEFAULT_SORT,
    FACET_COUNT_BASIS,
    FACET_DIMENSIONS,
    SORT_FIELDS,
    build_facets,
    build_stats,
    filing_year,
    filter_documents,
    sort_documents,
)


def _row(
    document_id: str,
    *,
    ticker: str | None = "AAPL",
    filing_date: str | None = "2025-10-31",
    report_date: str | None = "2025-09-27",
    sections: list[str] | None = None,
    chunk_count: int = 3,
) -> dict:
    return {
        "document_id": document_id,
        "ticker": ticker,
        "filing_date": filing_date,
        "report_date": report_date,
        "accession_number": document_id.split(":")[-1],
        "sections": ["business", "risk_factors"] if sections is None else sections,
        "chunk_count": chunk_count,
        "source_url": None,
    }


CATALOG = [
    _row("AAPL:0001", ticker="AAPL", filing_date="2025-10-31", sections=["business", "risk_factors"], chunk_count=10),
    _row("AAPL:0002", ticker="AAPL", filing_date="2024-11-01", sections=["business", "mdna"], chunk_count=5),
    _row("MSFT:0003", ticker="MSFT", filing_date="2024-09-30", sections=["risk_factors", "mdna"], chunk_count=7),
    _row("JPM:0004", ticker="JPM", filing_date="2023-02-21", sections=[], chunk_count=2, report_date=None),
]


@pytest.fixture
def client():
    """Inject a fixed catalog and a mock pipeline without running lifespan."""
    pipeline = MagicMock()
    pipeline.memory.get_stats.return_value = {"active_sessions": 0, "total_turns": 0}
    app_module._state.clear()
    app_module._state["pipeline"] = pipeline
    app_module._state["store"] = MagicMock()
    app_module._state["document_rows"] = [dict(row) for row in CATALOG]
    test_client = TestClient(app_module.app)
    yield test_client
    app_module._state.clear()


# --- Aggregation -----------------------------------------------------------


def test_filing_year_reads_only_a_real_filing_date() -> None:
    assert filing_year(_row("AAPL:0001")) == 2025
    assert filing_year({"filing_date": None}) is None
    assert filing_year({"filing_date": "unknown"}) is None
    assert filing_year({}) is None


def test_filters_combine_across_dimensions() -> None:
    assert [row["document_id"] for row in filter_documents(CATALOG, ticker="AAPL")] == [
        "AAPL:0001",
        "AAPL:0002",
    ]
    assert [row["document_id"] for row in filter_documents(CATALOG, year=2024)] == [
        "AAPL:0002",
        "MSFT:0003",
    ]
    assert [row["document_id"] for row in filter_documents(CATALOG, section="mdna")] == [
        "AAPL:0002",
        "MSFT:0003",
    ]
    assert [
        row["document_id"]
        for row in filter_documents(CATALOG, ticker="AAPL", section="business", year=2025)
    ] == ["AAPL:0001"]
    assert filter_documents(CATALOG, ticker="NVDA") == []


def test_sorting_is_deterministic_with_an_identifier_tiebreaker() -> None:
    rows = [
        _row("B:2", chunk_count=5),
        _row("A:1", chunk_count=5),
        _row("C:3", chunk_count=9),
    ]
    assert [row["document_id"] for row in sort_documents(rows, "chunk_count", "desc")] == [
        "C:3",
        "A:1",
        "B:2",
    ]
    assert [row["document_id"] for row in sort_documents(rows, "chunk_count", "asc")] == [
        "A:1",
        "B:2",
        "C:3",
    ]
    assert sort_documents(rows, "ticker") == sort_documents(rows, "ticker", "asc")
    with pytest.raises(ValueError):
        sort_documents(rows, "unknown-field")
    with pytest.raises(ValueError):
        sort_documents(rows, DEFAULT_SORT, "sideways")
    assert set(SORT_FIELDS) >= {"ticker", "filing_date", "chunk_count", "document_id"}


def test_facets_expose_recorded_values_in_deterministic_order() -> None:
    payload = build_facets(CATALOG)
    assert payload["count_basis"] == FACET_COUNT_BASIS
    assert [facet["dimension"] for facet in payload["facets"]] == list(FACET_DIMENSIONS)

    company, year, section = payload["facets"]
    assert [value["value"] for value in company["values"]] == ["AAPL", "JPM", "MSFT"]
    assert [value["count"] for value in company["values"]] == [2, 1, 1]
    # Years are ordered newest first and use real filing years only.
    assert [value["value"] for value in year["values"]] == [2025, 2024, 2023]
    assert [value["count"] for value in year["values"]] == [1, 2, 1]
    # Sections follow the canonical corpus order, not alphabetical order.
    assert [value["value"] for value in section["values"]] == [
        "business",
        "risk_factors",
        "mdna",
    ]
    assert [value["count"] for value in section["values"]] == [2, 2, 2]
    assert section["documents_without_value"] == 1
    for facet in payload["facets"]:
        assert facet["availability"] == "recorded"
        assert facet["reason"] is None


def test_facet_counts_exclude_only_their_own_dimension() -> None:
    payload = build_facets(CATALOG, ticker="AAPL")
    company, year, section = payload["facets"]

    # The company facet still counts every company (its own dimension is free)
    # while the other filters stay applied.
    assert [value["value"] for value in company["values"]] == ["AAPL", "JPM", "MSFT"]
    # The year facet keeps the ticker filter, so it only sees AAPL documents.
    assert [(value["value"], value["count"]) for value in year["values"]] == [(2025, 1), (2024, 1)]
    # The section facet keeps the ticker filter too.
    assert [(value["value"], value["count"]) for value in section["values"]] == [
        ("business", 2),
        ("risk_factors", 1),
        ("mdna", 1),
    ]
    assert payload["scope"]["documents"] == 2
    assert payload["scope"]["ticker"] == "AAPL"


def test_facet_counts_agree_with_the_total_without_their_own_dimension() -> None:
    for scope in ({}, {"ticker": "AAPL"}, {"section": "mdna"}, {"year": 2024}, {"ticker": "AAPL", "year": 2024}):
        payload = build_facets(CATALOG, **scope)
        assert payload["scope"]["documents"] == len(filter_documents(CATALOG, **scope))
        company, year, section = payload["facets"]

        without_company = {key: value for key, value in scope.items() if key != "ticker"}
        without_year = {key: value for key, value in scope.items() if key != "year"}
        without_section = {key: value for key, value in scope.items() if key != "section"}

        assert sum(value["count"] for value in company["values"]) == len(
            filter_documents(CATALOG, **without_company)
        )
        assert sum(value["count"] for value in year["values"]) + year[
            "documents_without_value"
        ] == len(filter_documents(CATALOG, **without_year))
        # A document can carry several sections, so a section facet counts per
        # section membership instead of summing to the document total.
        section_rows = filter_documents(CATALOG, **without_section)
        for value in section["values"]:
            assert value["count"] == sum(
                1 for row in section_rows if value["value"] in (row.get("sections") or [])
            )
        assert section["documents_without_value"] == sum(
            1 for row in section_rows if not row.get("sections")
        )
        assert max((value["count"] for value in section["values"]), default=0) <= len(section_rows)


def test_empty_catalog_reports_unknown_instead_of_fabricating_zero() -> None:
    payload = build_facets([])
    for facet in payload["facets"]:
        assert facet["values"] == []
        # An empty catalog is not evidence that a dimension is recorded.
        assert facet["availability"] == "unknown"
        assert facet["reason"] == "The catalog contains no documents."
    assert payload["scope"]["documents"] == 0

    stats = build_stats([])
    assert stats["documents"] == 0
    assert stats["companies"] == 0
    assert stats["chunks"] == 0
    assert stats["filing_type"]["value"] is None
    assert stats["filing_dates"]["availability"] == "unknown"
    assert stats["filing_dates"]["earliest"] is None
    assert stats["report_dates"]["availability"] == "unknown"
    assert stats["report_dates"]["reason"]
    assert stats["sections"]["availability"] == "unknown"
    # Configured-but-absent companies are reported, never silently omitted.
    assert len(stats["configured_companies_without_documents"]) == stats["configured_companies"]


def test_stats_distinguish_recorded_values_from_unknown_dimensions() -> None:
    stats = build_stats(CATALOG)
    assert stats["documents"] == 4
    assert stats["companies"] == 3
    assert stats["chunks"] == 24
    assert stats["filing_dates"]["availability"] == "recorded"
    assert stats["filing_dates"]["earliest"] == 2023
    assert stats["filing_dates"]["latest"] == 2025
    assert stats["filing_dates"]["documents_without_value"] == 0
    # One row has no report date; the dimension is still recorded by others.
    assert stats["report_dates"]["availability"] == "recorded"
    assert stats["report_dates"]["documents_with_value"] == 3
    # No stored artifact records a per-filing form type.
    assert stats["filing_type"] == {
        "availability": "unknown",
        "reason": stats["filing_type"]["reason"],
        "value": None,
    }
    assert stats["filing_type"]["reason"]
    assert stats["sections"]["documents_without_value"] == 1
    assert "AAPL" in stats["configured_companies_with_documents"]
    assert "NVDA" in stats["configured_companies_without_documents"]


def test_missing_optional_metadata_never_crashes_aggregation() -> None:
    rows = [
        {"document_id": "X:1", "ticker": None, "filing_date": None, "report_date": None, "sections": [], "chunk_count": None},
        {"document_id": "X:2"},
    ]
    payload = build_facets(rows)
    stats = build_stats(rows)

    company, year, section = payload["facets"]
    assert company["values"] == []
    assert year["documents_without_value"] == 2
    assert section["documents_without_value"] == 2
    assert stats["documents"] == 2
    assert stats["companies"] == 0
    assert stats["chunks"] == 0


# --- Endpoints -------------------------------------------------------------


def test_document_facets_endpoint_is_public_and_provider_free(client) -> None:
    response = client.get("/documents/facets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count_basis"] == FACET_COUNT_BASIS
    assert [facet["dimension"] for facet in payload["facets"]] == list(FACET_DIMENSIONS)
    assert payload["scope"]["documents"] == 4
    # The catalog route reads startup metadata only: nothing initialized or
    # called a model, provider, store, or reader.
    assert app_module._state["pipeline"].mock_calls == []


def test_document_facets_endpoint_applies_scope_and_validates_filters(client) -> None:
    scoped = client.get("/documents/facets", params={"ticker": "AAPL"})
    assert scoped.status_code == 200
    assert scoped.json()["scope"] == {
        "ticker": "AAPL",
        "section": None,
        "year": None,
        "filing_date": None,
        "search": None,
        "documents": 2,
    }

    assert client.get("/documents/facets", params={"ticker": "aapl"}).status_code == 422
    assert client.get("/documents/facets", params={"year": 1200}).status_code == 422
    assert client.get("/documents/facets", params={"search": "x" * 101}).status_code == 422


def test_document_stats_endpoint_reports_real_totals(client) -> None:
    response = client.get("/documents/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 4
    assert payload["companies"] == 3
    assert payload["chunks"] == 24
    assert payload["filing_type"]["value"] is None
    assert payload["generated_at"].endswith("Z")
    assert app_module._state["pipeline"].mock_calls == []


def test_documents_endpoint_accepts_year_and_sort_with_stable_order(client) -> None:
    by_year = client.get("/documents", params={"year": 2024})
    assert by_year.status_code == 200
    assert by_year.json()["total"] == 2
    assert [item["document_id"] for item in by_year.json()["items"]] == ["AAPL:0002", "MSFT:0003"]

    combined = client.get(
        "/documents",
        params={"ticker": "AAPL", "section": "business", "year": 2025, "sort": "filing_date", "direction": "desc"},
    )
    assert combined.status_code == 200
    assert combined.json()["total"] == 1
    assert combined.json()["sort"] == "filing_date"
    assert combined.json()["direction"] == "desc"

    sized = client.get("/documents", params={"sort": "chunk_count", "direction": "desc"})
    assert [item["chunk_count"] for item in sized.json()["items"]] == [10, 7, 5, 2]

    # Repeated identical requests return the same order.
    first = client.get("/documents", params={"sort": "ticker"}).json()
    second = client.get("/documents", params={"sort": "ticker"}).json()
    assert first == second


def test_documents_endpoint_rejects_an_unsupported_sort_field(client) -> None:
    response = client.get("/documents", params={"sort": "accession_number"})
    assert response.status_code == 422
    assert "Unsupported sort field" in response.json()["detail"]


def test_static_catalog_routes_precede_the_dynamic_document_route(client) -> None:
    # A document literally named "facets" or "stats" cannot shadow the static
    # catalog routes, and both stay reachable without a document lookup.
    assert client.get("/documents/facets").status_code == 200
    assert client.get("/documents/stats").status_code == 200
    assert client.get("/documents/NOT-A-DOCUMENT").status_code == 404


def test_catalog_responses_never_expose_private_workspace_data(client) -> None:
    for path in ("/documents", "/documents/facets", "/documents/stats"):
        encoded = client.get(path).text.casefold()
        for forbidden in ("conversation", "session_id", "workspace_mode", "token", "api_key", "sqlite"):
            assert forbidden not in encoded, f"{path} leaked {forbidden}"


def test_catalog_routes_report_not_ready_without_a_pipeline() -> None:
    app_module._state.clear()
    test_client = TestClient(app_module.app)
    # A server that has not loaded a corpus refuses the catalog instead of
    # claiming an empty one; the shared document routes behave the same way.
    assert test_client.get("/documents/facets").status_code == 503
    assert test_client.get("/documents/stats").status_code == 503
    assert test_client.get("/documents").status_code == 503


def test_scope_reason_codes_stay_machine_readable(client) -> None:
    payload = client.get("/documents/facets", params={"section": "risk_factors"}).json()
    assert payload["facets"][0]["availability"] == "recorded"
    # Documented contract: unknown dimensions carry a reason string, recorded
    # ones carry none.
    for facet in payload["facets"]:
        if facet["availability"] == "unknown":
            assert isinstance(facet["reason"], str) and facet["reason"]
        else:
            assert facet["reason"] is None
