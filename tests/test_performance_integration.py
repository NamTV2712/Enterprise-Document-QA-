"""OBS-001 owned boundaries, determinism, privacy and existing authority."""
import asyncio
import itertools
import json
import threading
import time
from contextlib import nullcontext
from dataclasses import asdict, replace
from datetime import timedelta

import pytest
from pydantic import ValidationError

from src.agent.durable import _job_id
from src.agent.errors import AgentToolError
from src.agent.evaluation import evaluate_durable_agent_run
from src.agent.registry import AgentToolRegistry, build_tool_registry
from src.api import app as application
from src.api.routers.agent_runs import _frames
from src.workspace.attribution import MAX_API_SPANS, PhaseSummary, TimingSummary, capture, persist_selected, span, statistics
from src.workspace.database import WorkspaceDatabase
from src.workspace.executors import AgentJobExecutor, ExecutorRegistry
from src.workspace.jobs import SQLiteJobRepository
from src.workspace.telemetry import SQLiteTelemetryRepository, TelemetryService, TelemetryValidationError
from src.workspace.worker import WorkerConfig, WorkerSupervisor
from tests.test_agent_durable import _create, _service
from tests.test_agent_orchestration import CHUNK, DOC, _final, _tool
from tests.test_agent_tools import DOCUMENT_ID, _context, _services
from tests.test_agent_provider import BEARER, KEY, FakeSDK, final, run, tool, wire
from tests.test_agent_provider_api import FALLBACK, configured
from tests.test_terminal_telemetry_api import _call, _configure_local, _headers


def test_deterministic_serialized_wait_is_separate_and_emits_after_release(tmp_path, monkeypatch):
    database = WorkspaceDatabase(tmp_path / "lock.sqlite3")
    database.initialize()
    original_lock = database._write_lock
    attempted, finished = threading.Event(), threading.Event()
    records, errors = [], []

    class Gate:
        def __enter__(self):
            attempted.set()
            original_lock.acquire()
        def __exit__(self, *_args):
            original_lock.release()
    database._write_lock = Gate()
    from src.workspace.attribution import Trace
    original_record = Trace.record
    def record(self, *args, **kwargs):
        assert not original_lock._is_owned()  # No telemetry lock under the DB lock.
        return original_record(self, *args, **kwargs)
    monkeypatch.setattr(Trace, "record", record)

    def operation():
        try:
            with capture("api") as trace:
                with database.transaction(write=True) as connection:
                    connection.execute("SELECT 1").fetchone()
            records.extend(trace.records)
        except BaseException as error:
            errors.append(error)
        finally:
            finished.set()
    original_lock.acquire()
    thread = threading.Thread(target=operation)
    thread.start()
    try:
        assert attempted.wait(5)
        assert not finished.is_set()
        released = time.perf_counter_ns()
    finally:
        original_lock.release()
    assert finished.wait(5)
    thread.join()
    assert not errors
    wait = next(row for row in records if row.phase == "workspace.serialized_wait")
    transaction = next(row for row in records if row.phase == "workspace.transaction")
    assert wait.start_ns <= released <= wait.end_ns <= transaction.start_ns
    assert wait.duration_ms > 0 and transaction.duration_ms >= 0


@pytest.mark.parametrize("name,args", [
    ("search_documents", {"query": "revenue"}),
    ("inspect_retrieval", {"question": "Find revenue"}),
    ("read_document", {"document_id": DOCUMENT_ID}),
    ("ask_rag", {"question": "Find revenue"}),
])
@pytest.mark.parametrize("fail", [False, True])
def test_all_four_tool_outcomes_are_content_free(name, args, fail):
    registry = build_tool_registry(_services([]))
    if fail:
        def broken(_body):
            raise RuntimeError("PROVIDER_CONTENT_SECRET_synthetic_only")
        registry = AgentToolRegistry(tuple(replace(tool, execute=broken) if tool.name == name else tool for tool in registry.list()))
    with capture("worker") as trace:
        if fail:
            with pytest.raises(AgentToolError):
                asyncio.run(registry.invoke(name, args, _context(name, provider=True)))
        else:
            asyncio.run(registry.invoke(name, args, _context(name, provider=True)))
    tool_span = next(row for row in trace.records if row.phase == "agent.tool." + name)
    assert tool_span.outcome == ("failed" if fail else "completed")
    encoded = trace.summary().model_dump_json()
    assert all(text not in encoded for text in ("revenue", "PROVIDER_CONTENT_SECRET", DOCUMENT_ID, "IGNORE ALL"))


def test_mocked_provider_timing_preserves_attempts_and_secret_guards():
    sdk = FakeSDK(wire(tool(document_id=DOC)), wire(final(refs=(("chunk_id", CHUNK),))))
    with capture("worker") as trace:
        result, _ = run(sdk)
    assert result.status == "completed"
    assert len(sdk.options) == 2 and all(options["max_retries"] == 0 for options in sdk.options)
    assert len([row for row in trace.records if row.phase == "agent.provider"]) == 2
    encoded = trace.summary().model_dump_json()
    for sentinel in (KEY, BEARER, "Bounded evidence summary.", "Find relevant risk evidence."):
        assert sentinel not in encoded
    poisoned = FakeSDK(wire(final(answer=KEY)))
    with capture("worker") as rejected:
        failure, _ = run(poisoned, require_observation=False)
    assert failure.status == "invalid_decision" and KEY not in failure.model_dump_json()
    assert KEY not in rejected.summary().model_dump_json()
    assert len(poisoned.options) == 1


@pytest.mark.parametrize("mode", ["success", "cancel", "failure"])
def test_on_off_identical_result_revision_events_error_and_evaluation(tmp_path, mode):
    snapshots = []
    for enabled in (False, True):
        counters = itertools.count(1)
        database = WorkspaceDatabase(tmp_path / str(enabled) / "semantic.sqlite3")
        database.initialize()
        repository = SQLiteJobRepository(database, clock=lambda: "2026-10-01T00:00:00Z", id_factory=lambda: f"fixed_{next(counters)}")
        decisions = (_tool("read_document", document_id=DOC), _final("Safe answer", ("chunk_id", CHUNK))) if mode == "success" else ()
        service, _, _, _, body = _service(tmp_path / str(enabled), decisions, repository=repository)
        with capture("worker") if enabled else nullcontext() as trace:
            created = _create(service, body)
            if mode == "cancel":
                result = service.cancel(created.run_id, expected_revision=created.revision)
            else:
                result = asyncio.run(service.run(created.run_id))
            events = service.events(created.run_id, after_sequence=0)
            report = evaluate_durable_agent_run(service, created.run_id)
            frames = list(_frames(events))
        assert len(report.metrics) == 21
        snapshots.append((result.model_dump(), [row.model_dump() for row in events], asdict(report), frames))
        if enabled:
            assert any(row.phase == "evaluation.compute" for row in trace.records)
            assert any(row.phase == "sse.serialize" for row in trace.records)
    assert snapshots[0] == snapshots[1]


def test_data005_population_retention_strict_summary_and_secret_rejection(tmp_path):
    database = WorkspaceDatabase(tmp_path / "telemetry.sqlite3")
    assert database.initialize() == 7
    repository = SQLiteTelemetryRepository(database, forbidden_secret_values=(KEY, BEARER))
    with capture("api") as trace:
        with span("api.total"):
            with span("api.access"):
                pass
    summary = trace.summary()
    repository.record_performance_terminal(summary=summary, correlation_id="req_safe", route_template="/agent/runs")
    now = repository.now()
    with database.connection() as connection:
        row = connection.execute("SELECT * FROM telemetry_events").fetchone()
        assert row["event_name"] == "performance_terminal"
        assert "start_ns" not in row["metadata_json"]
    assert not repository.request_records(started_at=now - timedelta(days=1), ended_at=now + timedelta(seconds=1))
    aggregate = TelemetryService(repository).summary("24h")["performance"]
    assert aggregate["terminal_count"] == 1 and aggregate["protocol"] == summary.protocol
    for identity in (KEY, BEARER):
        with pytest.raises(TelemetryValidationError):
            repository.record_performance_terminal(summary=summary, correlation_id=identity, route_template="/agent/runs")
    assert repository.prune_expired(now=now + timedelta(days=31)) == 1
    assert WorkspaceDatabase(database.path).initialize() == 7


def test_api_auth_totals_reads_evaluation_and_sse_do_not_capture_secrets(tmp_path, monkeypatch, caplog):
    _configure_local(monkeypatch, tmp_path)
    monkeypatch.setattr(application.settings, "enable_performance_attribution", True)
    captured = []
    monkeypatch.setattr(application.telemetry, "record_attribution", lambda trace, **_kwargs: captured.append(trace.summary()))
    service, repository, _, _, body = _service(tmp_path, (_tool("read_document", document_id=DOC), _final("SAFE_ANSWER", ("chunk_id", CHUNK))))
    monkeypatch.setattr(application, "_agent_durable_service", lambda: service)
    # The router closure references the original factory, whose nested owned
    # repository factory must retain its normal DB behavior.
    monkeypatch.setattr(application, "_agent_service_for_repository", lambda _repository: service)
    created = _create(service, body)
    asyncio.run(service.run(created.run_id))
    for suffix in ("", "/results", "/evaluation", "/events"):
        response = _call("GET", f"/agent/runs/{created.run_id}" + suffix, headers=_headers())
        assert response.status_code == 200
    assert len(captured) == 4
    assert all(any(row.phase == "api.total" for row in summary.phases) for summary in captured)
    assert any(row.phase == "sse.send" for summary in captured for row in summary.phases)
    assert any(row.phase == "evaluation.compute" for summary in captured for row in summary.phases)
    encoded = json.dumps(TelemetryService(SQLiteTelemetryRepository(repository.database)).summary("24h")) + str(captured) + caplog.text
    assert body.goal not in encoded and "SAFE_ANSWER" not in encoded
    assert KEY not in encoded and BEARER not in encoded
    resumed = _call("GET", f"/agent/runs/{created.run_id}/events", headers={**_headers(), "Last-Event-ID": "3"})
    sequences = [int(line[4:]) for line in resumed.text.splitlines() if line.startswith("id: ")]
    assert sequences == [event.sequence for event in service.events(created.run_id, after_sequence=3)]


def test_public_and_unauthorized_agent_requests_cannot_open_private_store(tmp_path, monkeypatch):
    _configure_local(monkeypatch, tmp_path)
    monkeypatch.setattr(application.settings, "enable_performance_attribution", True)
    assert _call("GET", "/agent/runs", headers=_headers(None)).status_code == 401
    assert not (tmp_path / "workspace.sqlite3").exists()
    monkeypatch.setattr(application.settings, "workspace_mode", "public")
    assert _call("GET", "/agent/runs", headers=_headers()).status_code == 404
    assert not (tmp_path / "workspace.sqlite3").exists()


def test_six_sentinels_across_real_api_worker_provider_and_durable_authorities(configured, monkeypatch, caplog):
    from tests.test_agent_api import _headers as agent_headers, _call as agent_call
    from tests.test_agent_orchestration import _services as agent_services
    sdk, calls = configured
    goal_text, document_text, provider_text = "GOAL_CONTENT_OBS_SENTINEL", "DOCUMENT_CONTENT_OBS_SENTINEL", "PROVIDER_CONTENT_OBS_SENTINEL"
    monkeypatch.setattr(application.settings, "enable_performance_attribution", True)
    monkeypatch.setattr(application, "create_agent_tool_registry", lambda: build_tool_registry(agent_services(calls, text=document_text)))
    sdk.outputs = [wire(tool(document_id=DOC)), wire(final(answer=provider_text, refs=(("chunk_id", CHUNK),)))]
    summaries = []
    monkeypatch.setattr(application.telemetry, "record_attribution", lambda trace, **_kwargs: summaries.append(trace.summary()))
    headers = agent_headers(token=BEARER)
    created = agent_call(application.app, "POST", "/agent/runs", headers=headers, body={"goal": goal_text, "allow_decision_provider_execution": True})
    assert created.status_code == 201
    identifier = created.json()["run_id"]
    service = application._agent_durable_service()
    async def execute():
        done = asyncio.Event()
        async def sink(trace, **kwargs):
            await application._publish_performance(trace, **kwargs)
            done.set()
        pool = WorkerSupervisor(service.repository, ExecutorRegistry((AgentJobExecutor(lambda: service),)), WorkerConfig(2, 100, 1000),
                                attribution_enabled=True, attribution_sink=sink)
        await pool.start()
        try:
            await asyncio.wait_for(done.wait(), 5)
        finally:
            await pool.stop()
    asyncio.run(execute())
    responses = [created]
    for suffix in ("", "/results", "/evaluation", "/events"):
        responses.append(agent_call(application.app, "GET", f"/agent/runs/{identifier}" + suffix, headers=headers))
    for endpoint in ("/analytics/summary", "/logs"):
        responses.append(agent_call(application.app, "GET", endpoint, headers=headers))
    assert all(response.status_code < 400 for response in responses)
    with service.repository.database.connection() as connection:
        telemetry_rows = [dict(row) for row in connection.execute("SELECT * FROM telemetry_events")]
        state_rows = [dict(row) for row in connection.execute("SELECT payload_json,result_json FROM jobs")]
        event_rows = [dict(row) for row in connection.execute("SELECT * FROM job_events")]
    content_free = json.dumps(telemetry_rows) + json.dumps(event_rows) + str(summaries) + caplog.text + responses[-2].text + responses[-1].text
    for sentinel in (KEY, FALLBACK, BEARER, goal_text, document_text, provider_text):
        assert sentinel not in content_free
    for secret in (KEY, FALLBACK, BEARER):
        assert secret not in json.dumps(state_rows) + "".join(response.text for response in responses)
    assert document_text not in json.dumps(state_rows)
    # Legitimate frozen goal/final answer stay in their existing product fields,
    # while OBS adds none of that content to state, events or telemetry.
    assert goal_text in state_rows[0]["payload_json"] and provider_text in state_rows[0]["result_json"]
    denied = agent_call(application.app, "POST", "/agent/runs", headers={**headers, "Idempotency-Key": "protected-obs"},
                        body={"goal": KEY, "allow_decision_provider_execution": True})
    assert denied.status_code == 422 and KEY not in denied.text
    assert len(sdk.options) == 2 and all(options["max_retries"] == 0 for options in sdk.options)


def test_worker_capture_fixed_capacity_claim_once_and_no_empty_poll_writes(tmp_path):
    async def exercise():
        service, repository, _, _, body = _service(tmp_path, (_tool("read_document", document_id=DOC), _final("Safe", ("chunk_id", CHUNK))))
        created = _create(service, body)
        completed = asyncio.Event()
        traces = []
        async def sink(trace, **_kwargs):
            traces.append(trace)
            completed.set()
        pool = WorkerSupervisor(repository, ExecutorRegistry((AgentJobExecutor(lambda: service),)), WorkerConfig(2, 100, 1000),
                                attribution_enabled=True, attribution_sink=sink)
        await pool.start()
        await asyncio.wait_for(completed.wait(), 5)
        assert pool.task_count == 2
        await pool.stop()
        assert len(traces) == 1
        assert service.get(created.run_id).state == "succeeded"
        phases = {row.phase for row in traces[0].records}
        assert {"worker.claim", "worker.service", "agent.decision", "agent.tool.read_document", "agent.persist_result"} <= phases
        events = service.events(created.run_id, after_sequence=0)
        assert sum(event.event_type == "state_changed" and event.state == "running" for event in events) == 1
        assert KEY not in traces[0].summary().model_dump_json()
        pool2 = WorkerSupervisor(repository, pool.registry, WorkerConfig(2, 100, 1000), attribution_enabled=True, attribution_sink=sink)
        await pool2.start()
        await pool2.stop()
        assert len(traces) == 1  # No terminal replay or empty-poll persistence.
    asyncio.run(exercise())


def test_root_survives_budget_and_signed_difference_statistics():
    with capture("api") as trace:
        with span("api.total"):
            for _ in range(MAX_API_SPANS * 2):
                with span("api.read"):
                    pass
    assert len(trace.records) == MAX_API_SPANS and trace.dropped > 0
    assert any(row.phase == "api.total" for row in trace.records)
    assert trace.summary().remainder_ms is None
    assert statistics([-2, 3], signed=True)["p50"] == -2
    assert statistics(range(19))["p95"] is None
    with pytest.raises(ValueError): statistics([float("nan")], signed=True)


def test_sampling_is_closed_server_owned_and_workers_always_persist(monkeypatch):
    from types import SimpleNamespace
    from src.workspace import attribution
    for integer in range(10):
        monkeypatch.setattr(attribution.uuid, "uuid4", lambda: SimpleNamespace(int=integer))
        assert persist_selected("api") == (integer == 0)
        assert persist_selected("worker")
    with pytest.raises(ValueError): persist_selected("user_input")


def test_performance_sink_reuses_initialized_store_without_rechecking_integrity(tmp_path, monkeypatch):
    _configure_local(monkeypatch, tmp_path)
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    monkeypatch.setattr(application, "persist_selected", lambda _source: True)
    monkeypatch.setattr(WorkspaceDatabase, "initialize", lambda _self: pytest.fail("observer reinitialized product store"))
    with capture("api") as trace:
        with span("api.total"):
            pass
    asyncio.run(application._publish_performance(trace, correlation_id="req_owned", route_template="/agent/runs"))
    with database.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0] == 1


def test_early_validation_measurement_never_initializes_a_new_store(tmp_path, monkeypatch):
    _configure_local(monkeypatch, tmp_path)
    monkeypatch.setattr(application, "persist_selected", lambda _source: True)
    with capture("api") as trace:
        with span("api.total"):
            pass
    asyncio.run(application._publish_performance(trace, correlation_id="req_owned", route_template="/agent/runs"))
    assert not (tmp_path / "workspace.sqlite3").exists()


@pytest.mark.parametrize("field,value", [("total_ms", float("inf")), ("max_ms", float("nan")), ("phase", "document_content"), ("count", 513)])
def test_summary_metadata_nonfinite_and_count_bounds(field, value):
    values = dict(phase="api.read", operation="none", count=1, total_ms=1.0, max_ms=1.0, completed=1, rejected=0, failed=0, cancelled=0)
    with pytest.raises(ValidationError): PhaseSummary(**{**values, field: value})
