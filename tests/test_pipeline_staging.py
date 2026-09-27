"""API-007 tests for provider-free pipeline staging over DATA-004 jobs."""

from __future__ import annotations

import asyncio
import itertools
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from configs.settings import Settings, settings
from src.api import access
from src.api import app as app_module
from src.api.pipeline import (
    PIPELINE_ID,
    PIPELINE_STAGES,
    PipelineDataError,
    PipelineInputNotFoundError,
    PipelineService,
    validate_pipeline_request,
)
from src.api.pipeline_models import PipelineRunCreateRequest
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository
from src.workspace.migrations import MIGRATIONS


TOKEN = "pipeline-test-token-0123456789abcdef"
ORIGIN = "http://localhost:3000"
CREATE_BODY = {"input_ids": ["AAPL"], "staging_profile": "isolated"}


async def _request(
    method: str,
    path: str,
    *,
    json: object | None = None,
    headers: dict[str, str] | None = None,
    peer: str = "127.0.0.1",
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app_module.app, client=(peer, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        return await client.request(method, path, json=json, headers=headers)


def _call(method: str, path: str, **kwargs) -> httpx.Response:
    return asyncio.run(_request(method, path, **kwargs))


def _repository(tmp_path: Path, *, name: str = "workspace.sqlite3") -> SQLiteJobRepository:
    database = WorkspaceDatabase(tmp_path / name)
    assert database.initialize() == 6
    counter = itertools.count(1)
    return SQLiteJobRepository(
        database,
        id_factory=lambda: f"pipeline-test-{next(counter):04d}",
        forbidden_secret_values=(),
    )


def _service(tmp_path: Path, *, configured: Settings | None = None) -> PipelineService:
    return PipelineService(_repository(tmp_path), configured or settings)


def _local(monkeypatch, tmp_path: Path, *, execution: bool = True) -> None:
    for configured in (access.settings, app_module.settings):
        monkeypatch.setattr(configured, "workspace_mode", "local")
        monkeypatch.setattr(configured, "local_workspace_token", SecretStr(TOKEN))
        monkeypatch.setattr(configured, "local_workspace_allowed_origins", ORIGIN)
        monkeypatch.setattr(configured, "local_workspace_allowed_hosts", "localhost:8000")
        monkeypatch.setattr(configured, "enable_workspace_execution", execution)
        monkeypatch.setattr(configured, "workspace_db_path", tmp_path / "workspace.sqlite3")


def _headers(*, token: str | None = TOKEN, host: str = "localhost:8000") -> dict[str, str]:
    headers = {"Host": host, "Origin": ORIGIN}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def test_definition_is_public_static_and_does_not_open_workspace(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(app_module.settings, "workspace_db_path", tmp_path / "never-opened.sqlite3")
    monkeypatch.setattr(app_module, "_pipeline_service", lambda: pytest.fail("opened private workspace"))

    response = _call("GET", "/pipeline")

    assert response.status_code == 200
    definition = response.json()
    assert definition["pipeline_id"] == PIPELINE_ID
    assert definition["staging_profiles"] == ["isolated"]
    assert [step["stage_id"] for step in definition["stages"]] == [
        stage.stage_id for stage in PIPELINE_STAGES
    ]
    assert definition["capabilities"]["executes_during_staging"] is False
    assert definition["capabilities"]["automatically_promotes_to_serving"] is False
    assert not (tmp_path / "never-opened.sqlite3").exists()


def test_request_validation_is_strict_and_unknown_ticker_is_not_a_storage_read(tmp_path) -> None:
    with pytest.raises(ValidationError):
        PipelineRunCreateRequest.model_validate(
            {**CREATE_BODY, "path": "D:/private/source"}
        )
    with pytest.raises(ValidationError):
        PipelineRunCreateRequest.model_validate(
            {"input_ids": ["AAPL"], "staging_profile": "canonical"}
        )
    duplicate = PipelineRunCreateRequest.model_validate(
        {"input_ids": ["AAPL", "AAPL"], "staging_profile": "isolated"}
    )
    with pytest.raises(ValueError, match="unique"):
        validate_pipeline_request(duplicate)
    unknown = PipelineRunCreateRequest.model_validate(
        {"input_ids": ["ZZZZZ"], "staging_profile": "isolated"}
    )
    with pytest.raises(PipelineInputNotFoundError):
        validate_pipeline_request(unknown)
    assert not (tmp_path / "workspace.sqlite3").exists()


def test_stage_is_idempotent_allowlisted_queued_and_provider_free(tmp_path, monkeypatch) -> None:
    service = _service(tmp_path)
    result = service.stage(PipelineRunCreateRequest.model_validate(CREATE_BODY))
    replay = service.stage(PipelineRunCreateRequest.model_validate(CREATE_BODY))

    assert replay.id == result.id
    assert result.state == "queued" and result.revision == 1
    assert result.configuration_fingerprint == result.configuration_fingerprint.lower()
    assert len(result.configuration_fingerprint) == 64
    assert result.progress.model_dump() == {"stage": None, "current": None, "total": None}
    assert result.artifact_references == []
    assert [step.stage_id for step in result.steps] == [stage.stage_id for stage in PIPELINE_STAGES]
    assert {step.state for step in result.steps} == {"pending"}
    assert all(step.revision == 1 for step in result.steps)
    stored = service.repository.get_job(result.id)
    assert stored.payload == {
        "pipeline_id": PIPELINE_ID,
        "input_ids": ["AAPL"],
        "staging_profile": "isolated",
    }
    assert stored.result is None and stored.progress.stage is None
    assert stored.artifact_references == ()
    assert service.repository.list_events(result.id)[0].event_type == "created"

    distinct = service.stage(
        PipelineRunCreateRequest.model_validate(
            {"input_ids": ["MSFT"], "staging_profile": "isolated"}
        )
    )
    assert distinct.id != result.id


def test_equivalent_concurrent_staging_requests_resolve_to_one_durable_run(tmp_path) -> None:
    path = tmp_path / "concurrent.sqlite3"
    database = WorkspaceDatabase(path)
    assert database.initialize() == 6
    configuration = settings.model_copy(deep=True)

    def stage_one() -> str:
        repository = SQLiteJobRepository(WorkspaceDatabase(path), forbidden_secret_values=())
        return PipelineService(repository, configuration).stage(
            PipelineRunCreateRequest.model_validate(CREATE_BODY)
        ).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        run_ids = list(pool.map(lambda _: stage_one(), range(8)))

    assert len(set(run_ids)) == 1
    assert SQLiteJobRepository(WorkspaceDatabase(path)).list_jobs(namespace="pipeline").total == 1


def test_configuration_fingerprint_changes_with_configured_embedding_binding(tmp_path) -> None:
    first = _service(
        tmp_path / "first",
        configured=settings.model_copy(
            update={"embedding_model_id": "fixture-embedder-a", "embedding_model_revision": "rev-a"}
        ),
    )
    second = _service(
        tmp_path / "second",
        configured=settings.model_copy(
            update={"embedding_model_id": "fixture-embedder-b", "embedding_model_revision": "rev-b"}
        ),
    )

    assert first._configuration_fingerprint() != second._configuration_fingerprint()


def test_persisted_pipeline_projection_rejects_wrong_namespace_shape_and_hides_result(tmp_path) -> None:
    service = _service(tmp_path)
    run = service.stage(PipelineRunCreateRequest.model_validate(CREATE_BODY))
    stored = service.repository.get_job(run.id)
    assert "result" not in run.model_dump()
    assert "payload" not in run.model_dump()
    assert "filesystem_path" not in run.model_dump()

    with pytest.raises(PipelineDataError):
        service._run_response(stored.__class__(**{**stored.__dict__, "job_type": "other"}))


def test_stage_and_private_routes_fail_closed_before_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(app_module.settings, "workspace_db_path", tmp_path / "private.sqlite3")
    public_read = _call("GET", "/pipeline/runs", headers=_headers())
    public_stage = _call("POST", "/pipeline/runs", json=CREATE_BODY, headers=_headers())
    definition = _call("GET", "/pipeline")

    assert public_read.status_code == 404
    assert public_stage.status_code == 404
    assert definition.status_code == 200
    assert not (tmp_path / "private.sqlite3").exists()

    _local(monkeypatch, tmp_path, execution=False)
    monkeypatch.setattr(app_module, "_pipeline_service", lambda: pytest.fail("opened private workspace"))
    no_token = _call("GET", "/pipeline/runs", headers=_headers(token=None))
    execution_disabled = _call("POST", "/pipeline/runs", json=CREATE_BODY, headers=_headers())
    wrong_port = _call("GET", "/pipeline/runs", headers=_headers(host="localhost:8001"))
    forwarded_spoof = _call(
        "GET",
        "/pipeline/runs",
        headers={**_headers(), "X-Forwarded-For": "127.0.0.1"},
        peer="203.0.113.7",
    )

    assert no_token.status_code == 401
    assert execution_disabled.status_code == 403
    assert wrong_port.status_code == 403
    assert forwarded_spoof.status_code == 403
    assert not (tmp_path / "workspace.sqlite3").exists()


def test_http_stage_list_detail_cancel_and_resumable_sse(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    created = _call("POST", "/pipeline/runs", json=CREATE_BODY, headers=_headers())
    assert created.status_code == 201
    run = created.json()
    assert created.headers["etag"] == '"1"'
    assert created.headers["access-control-expose-headers"] == "ETag"
    assert run["state"] == "queued" and run["revision"] == 1
    assert "payload" not in run and "result" not in run
    assert run["artifact_references"] == []
    assert [step["stage_id"] for step in run["steps"]] == [stage.stage_id for stage in PIPELINE_STAGES]

    replay = _call("POST", "/pipeline/runs", json=CREATE_BODY, headers=_headers())
    other = _call(
        "POST",
        "/pipeline/runs",
        json={"input_ids": ["MSFT"], "staging_profile": "isolated"},
        headers=_headers(),
    )
    listed = _call("GET", "/pipeline/runs?state=queued", headers=_headers())
    detail = _call("GET", f"/pipeline/runs/{run['id']}", headers=_headers())
    assert replay.json()["id"] == run["id"]
    assert other.json()["id"] != run["id"]
    assert listed.status_code == 200 and listed.json()["total"] == 2
    assert detail.status_code == 200 and detail.headers["etag"] == '"1"'

    missing_precondition = _call(
        "POST", f"/pipeline/runs/{run['id']}/cancel", headers=_headers()
    )
    cancelled = _call(
        "POST",
        f"/pipeline/runs/{run['id']}/cancel",
        headers={**_headers(), "If-Match": '"1"'},
    )
    stale = _call(
        "POST",
        f"/pipeline/runs/{run['id']}/cancel",
        headers={**_headers(), "If-Match": '"1"'},
    )
    assert missing_precondition.status_code == 428
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled" and cancelled.json()["revision"] == 2
    assert cancelled.headers["etag"] == '"2"'
    assert stale.status_code == 409

    first_events = _call("GET", f"/pipeline/runs/{run['id']}/events", headers=_headers())
    assert first_events.status_code == 200
    assert first_events.headers["content-type"].startswith("text/event-stream")
    assert "id: 1\nevent: created\n" in first_events.text
    assert "id: 2\nevent: cancellation_requested\n" in first_events.text
    resumed = _call(
        "GET",
        f"/pipeline/runs/{run['id']}/events",
        headers={**_headers(), "Last-Event-ID": "1"},
    )
    assert "id: 1\n" not in resumed.text and "id: 2\n" in resumed.text
    malformed = _call(
        "GET",
        f"/pipeline/runs/{run['id']}/events",
        headers={**_headers(), "Last-Event-ID": "1,2"},
    )
    assert malformed.status_code == 422

    reopened = SQLiteJobRepository(WorkspaceDatabase(tmp_path / "workspace.sqlite3"))
    persisted = reopened.get_job(run["id"])
    assert persisted.state == "cancelled" and persisted.revision == 2
    assert reopened.database.current_schema_version() == MIGRATIONS[-1].version == 6


def test_running_cancellation_remains_cancelling_until_acknowledged(tmp_path) -> None:
    service = _service(tmp_path)
    queued = service.stage(PipelineRunCreateRequest.model_validate(CREATE_BODY))
    running = service.repository.transition_job(
        queued.id,
        expected_revision=queued.revision,
        target_state="running",
    )

    requested = service.cancel_run(running.job_id, expected_revision=running.revision)

    assert requested.state == "cancelling"
    assert requested.revision == running.revision + 1
    assert {step.state for step in requested.steps} == {"pending"}


def test_cancel_requires_execution_capability_and_does_not_touch_job_when_disabled(
    monkeypatch, tmp_path
) -> None:
    _local(monkeypatch, tmp_path)
    created = _call("POST", "/pipeline/runs", json=CREATE_BODY, headers=_headers())
    assert created.status_code == 201
    monkeypatch.setattr(access.settings, "enable_workspace_execution", False)
    monkeypatch.setattr(app_module, "_pipeline_service", lambda: pytest.fail("opened private workspace"))

    denied = _call(
        "POST",
        f"/pipeline/runs/{created.json()['id']}/cancel",
        headers={**_headers(), "If-Match": '"1"'},
    )

    assert denied.status_code == 403
    repository = SQLiteJobRepository(WorkspaceDatabase(tmp_path / "workspace.sqlite3"))
    assert repository.get_job(created.json()["id"]).state == "queued"


@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        ({"input_ids": ["AAPL", "AAPL"], "staging_profile": "isolated"}, 422),
        ({"input_ids": ["ZZZZZ"], "staging_profile": "isolated"}, 404),
        ({"input_ids": ["AAPL"], "staging_profile": "isolated", "path": "D:/secret"}, 422),
        ({"input_ids": ["AAPL"], "staging_profile": "canonical"}, 422),
    ],
)
def test_stage_validation_statuses_precede_database_creation(
    monkeypatch, tmp_path, body, expected_status
) -> None:
    _local(monkeypatch, tmp_path)
    response = _call(
        "POST",
        "/pipeline/runs",
        json=body,
        headers=_headers(),
    )
    assert response.status_code == expected_status
    assert not (tmp_path / "workspace.sqlite3").exists()


def test_bad_filters_headers_and_missing_runs_are_bounded(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    invalid_state = _call("GET", "/pipeline/runs?state=unknown", headers=_headers())
    invalid_last_id = _call(
        "GET",
        "/pipeline/runs/job-missing/events",
        headers={**_headers(), "Last-Event-ID": "-1"},
    )
    missing_run = _call("GET", "/pipeline/runs/job-missing", headers=_headers())

    assert invalid_state.status_code == 422
    assert invalid_last_id.status_code == 422
    assert missing_run.status_code == 404


def test_sse_replay_is_bounded_and_reconnects_after_returned_sequence(monkeypatch, tmp_path) -> None:
    _local(monkeypatch, tmp_path)
    created = _call("POST", "/pipeline/runs", json=CREATE_BODY, headers=_headers())
    assert created.status_code == 201
    run_id = created.json()["id"]
    repository = SQLiteJobRepository(WorkspaceDatabase(tmp_path / "workspace.sqlite3"))
    running = repository.transition_job(run_id, expected_revision=1, target_state="running")
    for current in range(101):
        running = repository.report_progress(
            run_id,
            expected_revision=running.revision,
            stage="download_filings",
            current=current,
            total=101,
        )

    first = _call("GET", f"/pipeline/runs/{run_id}/events", headers=_headers())
    resumed = _call(
        "GET",
        f"/pipeline/runs/{run_id}/events",
        headers={**_headers(), "Last-Event-ID": "100"},
    )

    first_ids = [line for line in first.text.splitlines() if line.startswith("id: ")]
    resumed_ids = [line for line in resumed.text.splitlines() if line.startswith("id: ")]
    assert len(first_ids) == 100
    assert first_ids[0] == "id: 1" and first_ids[-1] == "id: 100"
    assert resumed_ids[0] == "id: 101" and resumed_ids[-1] == f"id: {running.revision}"


def test_pipeline_revision_and_event_headers_pass_cors_preflight() -> None:
    cancel = _call(
        "OPTIONS",
        "/pipeline/runs/example/cancel",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,if-match",
        },
    )
    events = _call(
        "OPTIONS",
        "/pipeline/runs/example/events",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,last-event-id",
        },
    )

    assert cancel.status_code == events.status_code == 200
    assert "if-match" in cancel.headers["access-control-allow-headers"].casefold()
    assert "last-event-id" in events.headers["access-control-allow-headers"].casefold()
