"""API-002 structural contracts for route extraction and dependency ownership."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.api import app as app_module
from src.api import schemas


EXPECTED_ROUTE_ORDER = [
    ("GET", "/health/live"),
    ("GET", "/system/configuration-status"),
    ("GET", "/health/ready"),
    ("GET", "/health"),
    ("POST", "/workspace/imports/preview"),
    ("POST", "/workspace/imports"),
    ("GET", "/workspace/export"),
    ("POST", "/query"),
    ("POST", "/query/decomposed"),
    ("POST", "/query/decomposed/stream"),
    ("GET", "/supported-tickers"),
    ("GET", "/documents"),
    # API-003 static catalog routes are registered before the dynamic document
    # routes so a facet path can never resolve as a document_id.
    ("GET", "/documents/facets"),
    ("GET", "/documents/stats"),
    ("GET", "/documents/{document_id}"),
    ("GET", "/documents/{document_id}/chunks"),
    ("GET", "/chunks/{chunk_id}"),
    ("GET", "/documents/{document_id}/original"),
    ("GET", "/documents/{document_id}/reader"),
    ("GET", "/documents/{document_id}/reader/outline"),
    ("GET", "/documents/{document_id}/reader/content"),
    ("GET", "/documents/{document_id}/reader/search"),
    ("GET", "/documents/{document_id}/reader/section-export"),
    ("GET", "/documents/{document_id}/pdf"),
    ("POST", "/documents/{document_id}/pdf"),
    ("GET", "/documents/{document_id}/pdf/content"),
    ("GET", "/documents/{document_id}/pdf/mapping"),
    ("GET", "/documents/{document_id}/pdf/mapping/location"),
    ("GET", "/documents/{document_id}/original/content"),
    ("GET", "/chunks/{chunk_id}/original-location"),
    ("GET", "/chunks/{chunk_id}/reader-location"),
    ("GET", "/documents/{document_id}/original/search"),
    # API-004 discovery routes: the snapshot read is the only dynamic /search
    # path and is registered after the static create route.
    ("POST", "/search"),
    ("GET", "/search/{search_id}"),
    ("GET", "/system/info"),
    ("GET", "/evaluation/runs"),
    ("GET", "/evaluation/runs/{run_id}"),
    ("POST", "/retrieval/inspect"),
    ("DELETE", "/session/{session_id}"),
    ("GET", "/session/{session_id}/history"),
    ("GET", "/cache/stats"),
    ("GET", "/metrics"),
    ("POST", "/cache/clear"),
    ("POST", "/cache/test"),
    ("POST", "/query/stream"),
]

EXTRACTED_ROUTE_MODULES = {
    "/health/live": "src.api.routers.health",
    "/system/configuration-status": "src.api.routers.health",
    "/health/ready": "src.api.routers.health",
    "/health": "src.api.routers.health",
    "/supported-tickers": "src.api.routers.corpus",
    "/system/info": "src.api.routers.system",
    "/evaluation/runs": "src.api.routers.evaluations",
    "/evaluation/runs/{run_id}": "src.api.routers.evaluations",
    "/session/{session_id}": "src.api.routers.sessions",
    "/session/{session_id}/history": "src.api.routers.sessions",
    "/cache/stats": "src.api.routers.cache",
    "/metrics": "src.api.routers.cache",
    "/cache/clear": "src.api.routers.cache",
    "/cache/test": "src.api.routers.cache",
}

MOVED_OPENAPI_SHA256 = "5c4098c68832465a2e8db8f3fc6441cb4ce777399d2711976a20145ebf35ae16"


def _application_routes() -> list[APIRoute]:
    return [route for route in app_module.app.routes if isinstance(route, APIRoute)]


def test_complete_route_order_and_methods_are_preserved() -> None:
    actual = [
        (next(iter(route.methods)), route.path)
        for route in _application_routes()
    ]

    assert actual == EXPECTED_ROUTE_ORDER
    assert len(actual) == len(set(actual))


def test_extracted_routes_have_coherent_transport_owners() -> None:
    routes = {route.path: route for route in _application_routes()}

    assert {
        path: routes[path].endpoint.__module__
        for path in EXTRACTED_ROUTE_MODULES
    } == EXTRACTED_ROUTE_MODULES
    assert app_module.QueryRequest is schemas.QueryRequest
    assert app_module.QueryResponse is schemas.QueryResponse
    assert app_module.RetrievalInspectRequest is schemas.RetrievalInspectRequest


def test_api003_catalog_routes_have_coherent_transport_owners() -> None:
    routes = {route.path: route for route in _application_routes()}

    assert {
        path: routes[path].endpoint.__module__
        for path in ("/documents/facets", "/documents/stats")
    } == {
        "/documents/facets": "src.api.routers.catalog",
        "/documents/stats": "src.api.routers.catalog",
    }
    # The catalog router receives an application-owned callback and never
    # constructs a model, provider, store, or reader of its own.
    assert "/documents" in routes
    assert routes["/documents"].endpoint.__module__ == "src.api.app"


def test_api004_discovery_routes_have_coherent_transport_owners() -> None:
    routes = {route.path: route for route in _application_routes()}

    assert routes["/search"].endpoint.__module__ == "src.api.routers.search"
    assert routes["/search/{search_id}"].endpoint.__module__ == "src.api.routers.search"
    # The router is built over an application-owned service callback, so the
    # module never constructs a retriever, model, or store itself.
    assert app_module._discovery_service.__module__ == "src.api.app"


def test_moved_openapi_operations_match_the_pre_extraction_contract() -> None:
    specification = app_module.app.openapi()
    contracts = {
        path: specification["paths"][path]
        for path in sorted(EXTRACTED_ROUTE_MODULES)
    }
    encoded = json.dumps(
        contracts, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    assert hashlib.sha256(encoded).hexdigest() == MOVED_OPENAPI_SHA256


def test_static_evaluation_route_precedes_dynamic_and_keeps_errors(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(app_module.settings, "data_public_evaluations_dir", tmp_path)
    client = TestClient(app_module.app)
    listing = client.get("/evaluation/runs")
    invalid = client.get("/evaluation/runs", params={"page": 0})
    missing = client.get("/evaluation/runs/not-published")

    assert listing.status_code == 200
    assert listing.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert invalid.status_code == 422
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Evaluation run not found"}


def test_extracted_public_reads_remain_provider_free_and_keep_request_id(
    tmp_path, monkeypatch
) -> None:
    pipeline = MagicMock()
    pipeline.memory.get_stats.return_value = {"active_sessions": 0, "total_turns": 0}
    pipeline.retriever.embedder.model_name = "fixture-embedder"
    pipeline.retriever.cross_encoder_model = "fixture-reranker"
    monkeypatch.setattr(app_module.settings, "data_public_evaluations_dir", tmp_path)
    app_module._state.clear()
    app_module._state.update(
        {
            "pipeline": pipeline,
            "supported_tickers": ["AAPL"],
            "corpus": {"searchable_company_count": 1, "indexed_chunk_count": 2},
        }
    )
    try:
        client = TestClient(app_module.app)
        health = client.get("/health", headers={"X-Request-ID": "api-002"})
        tickers = client.get("/supported-tickers")
        system = client.get("/system/info")
        evaluations = client.get("/evaluation/runs")
    finally:
        app_module._state.clear()

    assert health.status_code == 200
    assert health.headers["x-request-id"] == "api-002"
    assert tickers.json()["tickers"] == ["AAPL"]
    assert system.json()["retrieval"]["embedding_model"] == "fixture-embedder"
    assert evaluations.status_code == 200
    pipeline.query.assert_not_called()
    pipeline.retriever.inspect.assert_not_called()
