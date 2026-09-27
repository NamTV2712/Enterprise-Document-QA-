"""Focused DATA-005 access, route, and real request-lifecycle integration tests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from src.api import access
from src.api import app as app_module
from src.api.telemetry import RequestTelemetry
from src.workspace.database import WorkspaceDatabase
from src.workspace.telemetry import SQLiteTelemetryRepository, TelemetryService


TOKEN = "telemetry-test-token-0123456789-abcdef"
ORIGIN = "http://localhost:3000"
HOST = "localhost:8000"


async def _request(
    method: str,
    path: str,
    *,
    json: object | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app_module.app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        return await client.request(method, path, json=json, headers=headers)


def _call(method: str, path: str, **kwargs) -> httpx.Response:
    return asyncio.run(_request(method, path, **kwargs))


def _configure_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for configured in (access.settings, app_module.settings):
        monkeypatch.setattr(configured, "workspace_mode", "local")
        monkeypatch.setattr(configured, "local_workspace_token", SecretStr(TOKEN))
        monkeypatch.setattr(configured, "local_workspace_allowed_origins", ORIGIN)
        monkeypatch.setattr(configured, "local_workspace_allowed_hosts", HOST)
        monkeypatch.setattr(configured, "workspace_db_path", tmp_path / "workspace.sqlite3")


def _headers(token: str | None = TOKEN) -> dict[str, str]:
    headers = {"Host": HOST, "Origin": ORIGIN}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _pipeline() -> MagicMock:
    pipeline = MagicMock()
    pipeline.query.return_value = SimpleNamespace(
        answer="Synthetic answer.",
        model_used="synthetic-model",
        retrieved_chunks=[],
        answer_language="en",
        visual_answer=None,
    )
    pipeline.query_stream.return_value = iter(
        [
            ("token", "Synthetic answer."),
            (
                "done",
                {
                    "request_id": "server-stream",
                    "request_status": "completed",
                    "model_used": "synthetic-model",
                    "num_chunks_retrieved": 0,
                },
            ),
        ]
    )
    return pipeline


def test_public_mode_hides_private_telemetry_and_never_creates_workspace(tmp_path: Path, monkeypatch) -> None:
    for configured in (access.settings, app_module.settings):
        monkeypatch.setattr(configured, "workspace_mode", "public")
        monkeypatch.setattr(configured, "workspace_db_path", tmp_path / "never-created.sqlite3")

    responses = [
        _call("GET", "/analytics/summary", headers=_headers()),
        _call("GET", "/analytics/timeseries", headers=_headers()),
        _call("GET", "/logs", headers=_headers()),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert all(response.json() == {"detail": "Local workspace capability is unavailable"} for response in responses)
    assert not (tmp_path / "never-created.sqlite3").exists()


def test_private_routes_require_shared_local_bearer_and_return_typed_empty_truth(tmp_path: Path, monkeypatch) -> None:
    _configure_local(monkeypatch, tmp_path)

    assert _call("GET", "/analytics/summary", headers=_headers(None)).status_code == 401
    assert _call("GET", "/analytics/summary", headers=_headers("wrong-token")).status_code == 401
    summary = _call("GET", "/analytics/summary?range=24h", headers=_headers())
    series = _call(
        "GET",
        "/analytics/timeseries?range=24h&interval=hour&metric=request_duration_p95_ms",
        headers=_headers(),
    )
    logs = _call("GET", "/logs?limit=10", headers=_headers())

    assert summary.status_code == series.status_code == logs.status_code == 200
    assert summary.json()["requests"]["terminal_count"] == 0
    assert summary.json()["requests"]["success_rate"]["value"] is None
    assert all(point["value"] is None for point in series.json()["points"])
    assert logs.json() == {"items": [], "next_cursor": None, "has_more": False, "limit": 10}
    encoded = str(summary.json()) + str(series.json()) + str(logs.json())
    assert TOKEN not in encoded


@pytest.mark.parametrize(
    "path",
    [
        "/analytics/summary?range=all",
        "/analytics/timeseries?metric=cost_usd",
        "/logs?category=debug",
        "/logs?level=critical",
        "/logs?limit=101",
        "/logs?cursor=not-base64",
    ],
)
def test_private_query_selectors_are_closed_and_bounded(
    tmp_path: Path,
    monkeypatch,
    path: str,
) -> None:
    _configure_local(monkeypatch, tmp_path)

    response = _call("GET", path, headers=_headers())

    assert response.status_code == 422


def test_real_non_streaming_query_writes_one_content_free_terminal_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_local(monkeypatch, tmp_path)
    pipeline = _pipeline()
    app_module._state.clear()
    app_module._state["pipeline"] = pipeline
    try:
        response = _call(
            "POST",
            "/query",
            json={"question": "What private revenue text must never persist?", "top_k": 3},
            headers={"X-Request-ID": TOKEN},
        )
    finally:
        app_module._state.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"] != TOKEN
    repository = SQLiteTelemetryRepository(
        WorkspaceDatabase(tmp_path / "workspace.sqlite3"),
        forbidden_secret_values=(TOKEN,),
    )
    assert repository.database.initialize() == 6
    with repository.database.connection() as connection:
        rows = connection.execute("SELECT * FROM telemetry_events").fetchall()
    assert len(rows) == 1
    assert rows[0]["route_template"] == "/query"
    assert rows[0]["status"] == "succeeded"
    assert rows[0]["severity"] == "info"
    assert rows[0]["duration_ms"] is not None
    raw = (tmp_path / "workspace.sqlite3").read_bytes()
    assert b"private revenue" not in raw
    assert TOKEN.encode() not in raw


def test_real_stream_records_terminal_after_done_not_when_headers_open(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_local(monkeypatch, tmp_path)
    pipeline = _pipeline()
    app_module._state.clear()
    app_module._state["pipeline"] = pipeline
    try:
        response = _call(
            "POST",
            "/query/stream",
            json={"question": "Stream a synthetic answer", "top_k": 3},
        )
    finally:
        app_module._state.clear()

    assert response.status_code == 200
    assert '"type": "done"' in response.text
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    assert database.initialize() == 6
    with database.connection() as connection:
        rows = connection.execute("SELECT * FROM telemetry_events").fetchall()
    assert len(rows) == 1
    assert rows[0]["route_template"] == "/query/stream"
    assert rows[0]["status"] == "succeeded"
    assert json.loads(rows[0]["metadata_json"])["streaming"] is True


def test_telemetry_write_failure_is_best_effort_and_does_not_change_source_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_local(monkeypatch, tmp_path)
    pipeline = _pipeline()
    app_module._state.clear()
    app_module._state["pipeline"] = pipeline
    monkeypatch.setattr(
        app_module,
        "_terminal_telemetry_service",
        lambda: (_ for _ in ()).throw(RuntimeError("synthetic storage failure")),
    )
    try:
        response = _call(
            "POST",
            "/query",
            json={"question": "Still return the real source response", "top_k": 3},
        )
    finally:
        app_module._state.clear()

    assert response.status_code == 200
    assert response.json()["answer"] == "Synthetic answer."
    assert not (tmp_path / "workspace.sqlite3").exists()


def test_private_log_route_exposes_only_structured_safe_fields(tmp_path: Path, monkeypatch) -> None:
    _configure_local(monkeypatch, tmp_path)
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    assert database.initialize() == 6
    repository = SQLiteTelemetryRepository(database, forbidden_secret_values=(TOKEN,))
    repository.record_request_terminal(
        telemetry_id="tel_safe_api",
        subsystem="retrieval",
        route_template="/retrieval/inspect",
        capability="public_provider_free",
        severity="warning",
        outcome="rejected",
        correlation_id="request-safe",
        duration_ms=None,
        error_code="http_422",
        metadata={"http_method": "POST", "streaming": False, "decomposed": False, "status_code": 422},
    )

    response = _call("GET", "/logs?category=request&level=warning", headers=_headers())
    summary = _call("GET", "/analytics/summary?range=24h", headers=_headers())

    assert response.status_code == 200
    assert summary.status_code == 200
    assert summary.json()["requests"]["terminal_count"] == 1
    item = response.json()["items"][0]
    assert item["kind"] == "request_terminal"
    assert item["route_template"] == "/retrieval/inspect"
    assert item["duration_ms"] is None
    assert set(item) == {
        "record_id", "occurred_at", "category", "level", "kind", "subsystem",
        "outcome", "correlation_id", "domain_id", "route_template", "error_code",
        "duration_ms", "metadata",
    }
    assert TOKEN not in str(item)


def test_legacy_opt_in_metrics_use_route_templates_not_private_operation_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure_local(monkeypatch, tmp_path)
    monkeypatch.setattr(app_module.settings, "enable_metrics_endpoint", True)
    previous = app_module.telemetry
    app_module.telemetry = RequestTelemetry()
    try:
        missing = _call(
            "GET",
            "/pipeline/runs/private-job-identity",
            headers=_headers(),
        )
        metrics = _call("GET", "/metrics")
    finally:
        app_module.telemetry = previous

    assert missing.status_code == 404
    assert metrics.status_code == 200
    routes = metrics.json()["requests_by_route"]
    assert routes["/pipeline/runs/{run_id}"] == 1
    assert "private-job-identity" not in str(routes)
