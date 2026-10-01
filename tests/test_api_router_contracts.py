"""API-002 structural contracts for route extraction and dependency ownership."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
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
    # DATA-003 typed collections are registered as their own protected group
    # after the workspace transfer routes. Collection detail and member paths
    # come after the list and create routes, so an item path can never resolve
    # as a collection_id.
    ("GET", "/collections"),
    ("POST", "/collections"),
    ("GET", "/collections/{collection_id}"),
    ("PATCH", "/collections/{collection_id}"),
    ("DELETE", "/collections/{collection_id}"),
    ("GET", "/collections/{collection_id}/items"),
    ("POST", "/collections/{collection_id}/items"),
    ("DELETE", "/collections/{collection_id}/items/{item_id}"),
    ("GET", "/collections/{collection_id}/notes"),
    ("POST", "/collections/{collection_id}/notes"),
    ("PATCH", "/collections/{collection_id}/notes/{note_id}"),
    ("DELETE", "/collections/{collection_id}/notes/{note_id}"),
    ("GET", "/collections/{collection_id}/activity"),
    ("GET", "/collections/{collection_id}/export"),
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
    ("GET", "/models"),
    ("POST", "/models/{model_id}/tests"),
    ("GET", "/datasets"),
    ("GET", "/datasets/{dataset_id}"),
    # API-007 exposes the provider-free definition before protected run views.
    ("GET", "/pipeline"),
    ("GET", "/pipeline/runs"),
    ("POST", "/pipeline/runs"),
    ("GET", "/pipeline/runs/{run_id}"),
    ("POST", "/pipeline/runs/{run_id}/cancel"),
    ("GET", "/pipeline/runs/{run_id}/events"),
    ("GET", "/evaluation/metrics"),
    ("GET", "/evaluation/metrics/trends"),
    ("GET", "/evaluation/runs"),
    ("GET", "/evaluation/runs/{run_id}"),
    ("GET", "/evaluation/runs/{run_id}/results"),
    ("POST", "/evaluation/compare"),
    ("GET", "/evaluation/failures"),
    ("GET", "/evaluation/jobs"),
    ("POST", "/evaluation/jobs"),
    ("GET", "/evaluation/jobs/{job_id}"),
    ("GET", "/evaluation/jobs/{job_id}/results"),
    ("POST", "/evaluation/jobs/{job_id}/cancel"),
    ("GET", "/evaluation/jobs/{job_id}/events"),
    ("GET", "/agent/runs"),
    ("POST", "/agent/runs"),
    ("GET", "/agent/runs/{run_id}"),
    ("GET", "/agent/runs/{run_id}/results"),
    ("GET", "/agent/runs/{run_id}/evaluation"),
    ("POST", "/agent/runs/{run_id}/cancel"),
    ("GET", "/agent/runs/{run_id}/events"),
    ("GET", "/analytics/summary"),
    ("GET", "/analytics/timeseries"),
    ("GET", "/logs"),
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


def test_api006_registry_routes_have_coherent_transport_owners() -> None:
    routes = {route.path: route for route in _application_routes()}

    for path in (
        "/models",
        "/models/{model_id}/tests",
        "/datasets",
        "/datasets/{dataset_id}",
    ):
        assert routes[path].endpoint.__module__ == "src.api.routers.registries"


def test_api007_pipeline_routes_have_coherent_transport_owners() -> None:
    expected = {
        ("GET", "/pipeline"),
        ("GET", "/pipeline/runs"),
        ("POST", "/pipeline/runs"),
        ("GET", "/pipeline/runs/{run_id}"),
        ("POST", "/pipeline/runs/{run_id}/cancel"),
        ("GET", "/pipeline/runs/{run_id}/events"),
    }
    owners = {
        (next(iter(route.methods)), route.path): route.endpoint.__module__
        for route in _application_routes()
        if (next(iter(route.methods)), route.path) in expected
    }
    assert owners == {key: "src.api.routers.pipeline" for key in expected}


def test_data005_telemetry_routes_have_coherent_transport_owners() -> None:
    routes = {route.path: route for route in _application_routes()}

    for path in ("/analytics/summary", "/analytics/timeseries", "/logs"):
        assert routes[path].endpoint.__module__ == "src.api.routers.telemetry"


def _moved_openapi_operations(specification: dict) -> dict:
    contracts = {
        path: specification["paths"][path]
        for path in sorted(EXTRACTED_ROUTE_MODULES)
    }
    # Native publications add a completeness filter, not a legacy promotion
    # status. Verify that single additive change, then retain the frozen
    # pre-extraction digest for every other operation field.
    contracts = json.loads(json.dumps(contracts))
    status_parameter = next(
        parameter for parameter in contracts["/evaluation/runs"]["get"]["parameters"]
        if parameter["name"] == "status"
    )
    status_enum = status_parameter["schema"]["anyOf"][0]["enum"]
    assert status_enum == ["official", "candidate", "historical", "complete", "incomplete"]
    status_enum.remove("complete")
    # Pydantic 2.10 omits this keyword for bare dict responses; 2.13 emits
    # true. Both permit extra properties. Preserve false and typed schemas,
    # and leave all other metadata and request/response constraints intact.
    for operations in contracts.values():
        for operation in operations.values():
            for response in operation.get("responses", {}).values():
                for media in response.get("content", {}).values():
                    schema = media.get("schema", {})
                    if schema.get("type") == "object":
                        schema.setdefault("additionalProperties", True)
    return contracts


def _contract_digest(contract: dict) -> str:
    encoded = json.dumps(
        contract, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _referenced_contract_schemas(specification: dict, operations: dict) -> dict:
    """Freeze transitive request/response schemas as well as their ref names."""
    referenced = {}

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            reference = value.get("$ref", "")
            if reference.startswith("#/components/schemas/"):
                name = reference.removeprefix("#/components/schemas/")
                if name not in referenced:
                    referenced[name] = specification["components"]["schemas"][name]
                    visit(referenced[name])
            for item in value.values():
                visit(item)

    visit(operations)
    return referenced


def test_moved_openapi_operations_match_the_pre_extraction_contract() -> None:
    specification = app_module.app.openapi()
    contracts = _moved_openapi_operations(specification)

    assert _contract_digest(contracts) == MOVED_OPENAPI_SHA256
    expected_schemas = json.loads(
        (Path(__file__).parent / "fixtures" / "moved_openapi_schemas.json").read_text(
            encoding="utf-8"
        )
    )
    assert _referenced_contract_schemas(specification, contracts) == expected_schemas


def test_moved_openapi_contract_accepts_only_the_observed_representation_difference() -> None:
    specification = json.loads(json.dumps(app_module.app.openapi()))
    for operations in specification["paths"].values():
        for operation in operations.values():
            for response in operation.get("responses", {}).values():
                for media in response.get("content", {}).values():
                    schema = media.get("schema", {})
                    if schema.get("type") == "object" and schema.get("additionalProperties") is True:
                        schema.pop("additionalProperties")
    assert _contract_digest(_moved_openapi_operations(specification)) == MOVED_OPENAPI_SHA256


@pytest.mark.parametrize("change", [
    "path", "method", "parameter", "required", "request_body", "status",
    "response_type", "response_field", "closed_object", "typed_extras", "security",
])
def test_moved_openapi_contract_still_rejects_semantic_changes(change: str) -> None:
    specification = json.loads(json.dumps(app_module.app.openapi()))
    paths = specification["paths"]
    operation = paths["/health"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    if change == "path":
        paths["/renamed-health"] = paths.pop("/health")
        with pytest.raises(KeyError):
            _moved_openapi_operations(specification)
        return
    if change == "method":
        paths["/health"]["post"] = paths["/health"].pop("get")
    elif change == "parameter":
        paths["/evaluation/runs"]["get"]["parameters"][0]["in"] = "header"
    elif change == "required":
        paths["/session/{session_id}"]["delete"]["parameters"][0]["required"] = False
    elif change == "request_body":
        paths["/cache/test"]["post"]["requestBody"]["required"] = False
    elif change == "status":
        operation["responses"]["201"] = operation["responses"].pop("200")
    elif change == "response_type":
        schema["type"] = "string"
    elif change == "response_field":
        schema["properties"] = {"changed": {"type": "integer"}}
    elif change == "closed_object":
        schema["additionalProperties"] = False
    elif change == "typed_extras":
        schema["additionalProperties"] = {"type": "string"}
    elif change == "security":
        operation["security"] = [{"bearer": []}]
    assert _contract_digest(_moved_openapi_operations(specification)) != MOVED_OPENAPI_SHA256


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
