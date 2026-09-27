"""TEST-002: shared expectations checked against live Python owners, not copies."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Annotated, get_args, get_type_hints

import pytest
from fastapi.routing import APIRoute
from pydantic import TypeAdapter

from src.api.app import app
from src.api.access import require_execution_access, require_local_workspace_access


CATALOG = json.loads((Path(__file__).parent / "fixtures/cross_layer_contracts.json").read_text(encoding="utf-8"))
ROUTES = {(method, route.path): route for route in app.routes if isinstance(route, APIRoute) for method in route.methods}
REQUESTS = json.loads((Path(__file__).parent / "fixtures/cross_layer_requests.json").read_text(encoding="utf-8"))
RESPONSES = json.loads((Path(__file__).parent / "fixtures/cross_layer_responses.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("contract", CATALOG["enums"], ids=lambda entry: entry["python"])
def test_python_enum_owner_matches_shared_contract(contract):
    module_name, name = contract["python"].split(":")
    symbol, _, field = name.partition(".")
    owner = getattr(importlib.import_module(module_name), symbol)
    if field:
        owner = get_type_hints(owner)[field]
    actual = tuple(owner) if contract.get("constant") else get_args(owner)
    assert actual and set(actual) == set(contract["values"])
    assert len(actual) == len(set(actual)), "duplicate contract values"


def _dependency_calls(dependant):
    return {dependant.call} | {call for child in dependant.dependencies for call in _dependency_calls(child)}


@pytest.mark.parametrize("contract", CATALOG["routes"], ids=lambda entry: entry["id"])
def test_live_route_method_access_schema_and_revision(contract):
    route = ROUTES[contract["method"], contract["path"]]
    dependencies = _dependency_calls(route.dependant)
    access = ("execution" if require_execution_access in dependencies else
              "local" if require_local_workspace_access in dependencies else "public")
    assert access == contract["access"]
    if "response" in contract:
        assert route.response_model.__name__ == contract["response"]
        operation = app.openapi()["paths"][contract["path"]][contract["method"].lower()]
        schema = operation["responses"][str(route.status_code or 200)]["content"]["application/json"]["schema"]
        assert schema["$ref"] == f"#/components/schemas/{contract['response']}"
    if "body" in contract:
        assert route.body_field.type_.__name__ == contract["body"]
    else:
        assert route.body_field is None
    if contract.get("revision") == "body":
        field = route.body_field.type_.model_fields["revision"]
        assert field.is_required()
        assert route.body_field.type_.model_json_schema()["properties"]["revision"]["minimum"] == 1
    if contract.get("revision") == "query":
        field = next(field for field in route.dependant.query_params if field.alias == "revision")
        assert field.required
    if contract.get("revision") == "If-Match" or "header" in contract:
        expected = contract.get("header", "If-Match")
        assert expected in {field.alias for field in route.dependant.header_params}


def test_catalog_names_are_unique_and_cover_every_completed_surface():
    assert len({route["id"] for route in CATALOG["routes"]}) == len(CATALOG["routes"])
    assert {route["path"].split("/")[1] for route in CATALOG["routes"]} == {
        "models", "datasets", "documents", "search", "retrieval", "collections",
        "pipeline", "evaluation", "analytics", "logs", "system", "workspace",
    }


@pytest.mark.parametrize("example", REQUESTS["requests"], ids=lambda entry: entry["id"])
def test_shared_frontend_requests_are_valid_for_live_backend_parameters(example):
    contract = next(entry for entry in CATALOG["routes"] if entry["id"] == example["id"])
    route = ROUTES[contract["method"], contract["path"]]
    if "body" in example:
        model = route.body_field.type_
        parsed = model.model_validate(example["body"])
        # Explicit false/zero/null/empty values cannot disappear in validation.
        assert {key: parsed.model_dump(mode="json")[key] for key in example["body"]} == example["body"]
    parameters = {field.alias: field for field in route.dependant.query_params}
    for name, value in example.get("query", {}).items():
        field = parameters[name]  # Unknown browser query names must fail here.
        annotation = field.field_info.annotation
        metadata = field.field_info.metadata
        adapter = TypeAdapter(Annotated[annotation, *metadata] if metadata else annotation)
        assert adapter.validate_python(value) == value
    headers = {field.alias for field in route.dependant.header_params}
    assert set(example.get("headers", {})) <= headers
    for field in route.dependant.path_params:
        TypeAdapter(field.field_info.annotation).validate_python(REQUESTS["ids"][field.alias])


@pytest.mark.parametrize("example", RESPONSES["responses"], ids=lambda entry: entry["id"])
def test_shared_api_responses_preserve_exact_edge_values(example):
    module, symbol = example["model"].split(":")
    model = getattr(importlib.import_module(module), symbol)
    adapter = TypeAdapter(model)
    decoded = json.loads(adapter.dump_json(adapter.validate_python(example["value"])))
    assert decoded == example["value"]
    if example["id"] == "nativeCase":
        assert decoded["metrics"][0]["value"] == 0
        assert decoded["metrics"][1]["value"] is False
        assert decoded["metrics"][2]["value"] is None


@pytest.mark.parametrize("example", RESPONSES["snippets"], ids=lambda entry: repr(entry["text"]))
def test_snippet_code_point_ranges_match_original_not_casefolded_text(example):
    from src.api.discovery import build_snippet

    snippet = build_snippet(example["text"], example["terms"])
    assert snippet.as_payload() == example["snippet"]
    assert [snippet.text[start:end] for start, end in snippet.ranges] == example["marked"]


def test_casefold_expansion_before_a_truncated_window_keeps_original_offsets():
    from src.api.discovery import build_snippet, SNIPPET_MAX_LENGTH, SNIPPET_MAX_RANGES

    text = "ß " * 60 + "revenue " + "tail " * 70
    snippet = build_snippet(text, ("revenue",))
    assert snippet.text.startswith("…") and snippet.text.endswith("…")
    assert len(snippet.text) <= SNIPPET_MAX_LENGTH + 2
    assert len(snippet.ranges) <= SNIPPET_MAX_RANGES
    assert [snippet.text[start:end] for start, end in snippet.ranges] == ["revenue"]
