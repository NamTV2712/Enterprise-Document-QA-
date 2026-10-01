"""Worker-owned Agent/API/provider journeys with deterministic boundaries."""

import asyncio
import json
from dataclasses import asdict
from types import SimpleNamespace

import httpx
import pytest

from src.agent.durable_models import AgentRunCreateRequest
from src.agent.evaluation import evaluate_durable_agent_run
from src.api import app as application
from src.workspace.executors import AgentJobExecutor, ExecutorRegistry
from src.workspace.worker import WorkerConfig, WorkerSupervisor
from tests.test_agent_api import _headers
from tests.test_agent_orchestration import CHUNK, DOC
from tests.test_agent_provider import BEARER, KEY, FakeSDK, final, tool, wire
from tests.test_agent_provider_api import configured  # Explicit opt-in fixture.
from tests.test_workspace_worker import asynchronous


class ObservedExecutor(AgentJobExecutor):
    def __init__(self, factory):
        super().__init__(factory)
        self.finished = asyncio.Event()
        self.invocations = []

    async def execute(self, job):
        self.invocations.append(job.job_id)
        try:
            await super().execute(job)
        finally:
            self.finished.set()


def worker(service, factory=None, *, concurrency=2, grace=1000):
    executor = ObservedExecutor(factory or (lambda: service))
    pool = WorkerSupervisor(service.repository, ExecutorRegistry((executor,)),
                            WorkerConfig(concurrency, 500, grace))
    return pool, executor


async def finish(pool, executor):
    await asyncio.wait_for(executor.finished.wait(), 10)
    await pool.stop()


@asynchronous
async def test_api_create_returns_and_client_closes_before_blocked_provider_release(configured):
    sdk, calls = configured
    entered, release = asyncio.Event(), asyncio.Event()
    async def hold(_request):
        entered.set()
        await release.wait()
        return wire(tool(document_id=DOC))
    sdk.outputs = [hold]
    service = application._agent_durable_service()
    pool, executor = worker(service)
    await pool.start()
    headers = _headers(token=BEARER)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app),
                                    base_url="http://localhost:8000") as client:
            response = await asyncio.wait_for(client.post("/agent/runs", headers=headers, json={
                "goal": "Find bounded evidence.", "allow_decision_provider_execution": True}), 5)
            assert response.status_code == 201 and response.json()["state"] == "queued"
            assert response.headers["etag"] == '"1"'
        # The request and its client have ended; a lifespan-independent worker owns execution.
        await asyncio.wait_for(entered.wait(), 5)
        run_id = response.json()["run_id"]
        running = service.get(run_id)
        assert running.state == "running" and len(sdk.requests) == 1
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app),
                                    base_url="http://localhost:8000") as client:
            stale = await client.post(f"/agent/runs/{run_id}/cancel", headers={**headers, "If-Match": '"1"'})
            assert stale.status_code == 409
            cancelled = await client.post(f"/agent/runs/{run_id}/cancel",
                headers={**headers, "If-Match": f'"{running.revision}"'})
            assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelling"
            assert service.get(run_id).result is None
            assert not release.is_set() and not calls
            release.set()
            await finish(pool, executor)
            terminal = service.get(run_id)
            assert terminal.state == "cancelled" and terminal.result.decision_call_count == 1
            assert not calls and len(sdk.requests) == len(executor.invocations) == 1
            events = await client.get(f"/agent/runs/{run_id}/events", headers=headers)
            resumed = await client.get(f"/agent/runs/{run_id}/events", headers={**headers, "Last-Event-ID": "2"})
            assert "event: created" in events.text and "event: cancelled" in events.text
            assert "id: 1\n" not in resumed.text and "id: 2\n" not in resumed.text
            sequences = [int(line[4:]) for line in events.text.splitlines() if line.startswith("id: ")]
            assert sequences == list(range(1, len(sequences) + 1))
            report = await client.get(f"/agent/runs/{run_id}/evaluation", headers=headers)
            assert report.status_code == 200 and len(report.json()["metrics"]) == 21
            assert len(sdk.requests) == 1
            assert all(secret not in response.text + events.text + report.text for secret in (KEY, BEARER))
    finally:
        release.set()
        await pool.stop()


@pytest.mark.parametrize("decision_grant,rag_grant", [(False,False),(False,True),(True,False),(True,True)])
@asynchronous
async def test_worker_preserves_both_provider_permissions(configured, decision_grant, rag_grant):
    sdk, calls = configured
    sdk.outputs = [wire(tool("ask_rag", question="Find bounded risk evidence?")),
                   wire(final(refs=(("chunk_id", CHUNK),)))]
    service = application._agent_durable_service()
    created = service.create(AgentRunCreateRequest(goal="Find bounded risk evidence.",
        allowed_tools=["search_documents", "inspect_retrieval", "read_document", "ask_rag"],
        allow_decision_provider_execution=decision_grant, allow_provider_tool_execution=rag_grant),
        idempotency_key="worker-permissions")
    pool, executor = worker(service)
    await pool.start()
    await finish(pool, executor)
    terminal = service.get(created.run_id)
    if not decision_grant:
        assert terminal.result.failure.code == "decision_provider_required"
        assert not sdk.requests and not calls
    elif not rag_grant:
        assert terminal.result.failure.code == "tool_provider_required"
        assert len(sdk.requests) == 1 and not calls
    else:
        assert terminal.state == "succeeded" and calls == ["ask_rag"] and len(sdk.requests) == 2


@asynchronous
async def test_worker_research_real_sdk_transport_and_provider_free_evaluation(configured, monkeypatch):
    from groq import AsyncGroq
    from src.agent import provider
    _, calls = configured
    attempts = []
    decisions = [tool("search_documents", "apple_risk", query="Apple risk", ticker="AAPL"),
                 tool("read_document", "apple_risk", document_id=DOC),
                 final(refs=(("document_id", DOC), ("chunk_id", CHUNK)))]
    def transport(request):
        content = json.loads(request.content)
        assert content["response_format"]["json_schema"]["strict"] is True
        assert "tools" not in content and content["include_reasoning"] is False
        assert KEY not in json.dumps(content) and BEARER not in json.dumps(content)
        attempts.append(content)
        return httpx.Response(200, json={"id":"scale001", "object":"chat.completion", "created":1,
            "model":content["model"], "choices":[{"index":0,"finish_reason":"stop", "message":{
                "role":"assistant", "content":wire(decisions.pop(0))}}]})
    def client(**options):
        assert options["max_retries"] == 0
        return AsyncGroq(**options, http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)))
    monkeypatch.setattr(provider, "AsyncGroq", client)
    service = application._agent_durable_service()
    created = service.create(AgentRunCreateRequest(goal="Research Apple risk evidence.",
        allow_decision_provider_execution=True, research={"objectives":[{
            "objective_id":"apple_risk", "question":"Find Apple risk evidence", "ticker_scope":"AAPL"}]}),
        idempotency_key="worker-research")
    pool, executor = worker(service)
    await pool.start()
    await finish(pool, executor)
    terminal = service.get(created.run_id)
    assert terminal.state == "succeeded" and terminal.result.decision_call_count == 3
    assert calls == ["search_documents", "read_document"] and len(attempts) == 3
    assert terminal.result.research.objectives[0].coverage == "sufficient"
    assert terminal.result.evidence_refs[0].value == DOC
    report = evaluate_durable_agent_run(service, created.run_id)
    assert len(report.metrics) == 21 and len(attempts) == 3
    surfaces = terminal.model_dump_json() + json.dumps(asdict(report)) + json.dumps([
        event.model_dump(mode="json") for event in service.events(created.run_id, after_sequence=0)])
    assert KEY not in surfaces and BEARER not in surfaces


@asynchronous
async def test_cancel_after_claim_before_executor_admission_has_no_provider_or_tool(configured):
    sdk, calls = configured
    service = application._agent_durable_service()
    run = service.create(AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True),
                         idempotency_key="claim-cancel")
    admitted, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    class Gated(AgentJobExecutor):
        async def execute(self, job):
            admitted.set()
            await release.wait()
            await super().execute(job)
            finished.set()
    pool = WorkerSupervisor(service.repository, ExecutorRegistry((Gated(lambda: service),)), WorkerConfig(2))
    await pool.start()
    await asyncio.wait_for(admitted.wait(), 5)
    current = service.get(run.run_id)
    assert current.state == "running"
    service.cancel(run.run_id, expected_revision=current.revision)
    release.set()
    await asyncio.wait_for(finished.wait(), 5)
    await pool.stop()
    assert service.get(run.run_id).state == "cancelled" and not sdk.requests and not calls


@asynchronous
async def test_queued_cancel_worker_calls_nothing(configured):
    sdk, calls = configured
    service = application._agent_durable_service()
    created = service.create(AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True),
                             idempotency_key="before-claim")
    service.cancel(created.run_id, expected_revision=1)
    pool, executor = worker(service)
    assert await pool._claim() is None
    await pool.start()
    await pool.stop()
    assert service.get(created.run_id).state == "cancelled"
    assert not executor.invocations and not sdk.requests and not calls


@pytest.mark.parametrize("change", ["unsupported", "missing", "policy"])
@asynchronous
async def test_binding_is_resolved_at_execution_time_and_never_upgraded(configured, monkeypatch, change):
    sdk, calls = configured
    service = application._agent_durable_service()
    created = service.create(AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True),
                             idempotency_key="execution-binding")
    identity = created.frozen.decision_provider
    if change == "unsupported":
        monkeypatch.setitem(application._state, "pipeline", SimpleNamespace(generator=SimpleNamespace(model="chat-only")))
    elif change == "missing":
        monkeypatch.setattr(application.settings, "groq_api_key", "")
    else:
        monkeypatch.setattr(application.settings, "groq_key_policy", "pool")
    pool, executor = worker(service, application._agent_durable_service)
    await pool.start()
    await finish(pool, executor)
    terminal = service.get(created.run_id)
    assert terminal.result.failure.code == "decision_provider_unavailable"
    assert terminal.frozen.decision_provider == identity and not sdk.requests and not calls


@asynchronous
async def test_shutdown_blocked_sdk_interrupted_no_replay_and_resources_close(configured):
    sdk, calls = configured
    entered, release = asyncio.Event(), asyncio.Event()
    async def hold(_request):
        entered.set()
        await release.wait()
        return wire(tool(document_id=DOC))
    sdk.outputs = [hold]
    service = application._agent_durable_service()
    run = service.create(AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True),
                         idempotency_key="shutdown-provider")
    pool, executor = worker(service, grace=100)
    await pool.start()
    await asyncio.wait_for(entered.wait(), 5)
    await asyncio.wait_for(pool.stop(), 5)
    terminal = service.get(run.run_id)
    assert terminal.state == "interrupted" and terminal.result is None
    assert sdk.closed == len(sdk.requests) == len(executor.invocations) == 1 and not calls
    assert not release.is_set() and pool.task_count == pool.active_count == 0
    assert not service.repository.recover_interrupted_jobs()
    await pool.start()
    await pool.stop()
    assert len(sdk.requests) == 1


@pytest.mark.parametrize("window", ["before_call", "after_effect_before_commit"])
@asynchronous
async def test_real_claim_crash_windows_recover_without_replaying_provider(configured, monkeypatch, window):
    sdk, calls = configured
    service = application._agent_durable_service()
    run = service.create(AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True),
                         idempotency_key="actual-crash-window")
    class ProcessLost(BaseException):
        pass
    class Crash(ObservedExecutor):
        async def execute(self, job):
            if window == "before_call":
                raise ProcessLost()
            await super().execute(job)
    if window == "after_effect_before_commit":
        def crash_commit(_job, _result):
            raise ProcessLost()
        monkeypatch.setattr(service, "_finish", crash_commit)
    executor = Crash(lambda: service)
    pool = WorkerSupervisor(service.repository, ExecutorRegistry((executor,)), WorkerConfig(1))
    await pool.start()
    await asyncio.wait_for(pool._stop.wait(), 5)
    await pool.stop()
    crashed = service.get(run.run_id)
    assert crashed.state == "running" and crashed.result is None
    assert len(sdk.requests) == (0 if window == "before_call" else 2)
    assert calls == ([] if window == "before_call" else ["read_document"])
    service.repository.recover_interrupted_jobs()
    assert service.get(run.run_id).state == "interrupted"
    await pool.start()
    await pool.stop()
    assert len(sdk.requests) == (0 if window == "before_call" else 2)


@pytest.mark.parametrize("mode,execution,enabled,expected", [
    ("public",False,True,False), ("public",True,True,False),
    ("local",False,True,False), ("local",True,False,False), ("local",True,True,True),
])
@asynchronous
async def test_lifespan_local_execution_gates_and_cleanup(tmp_path, monkeypatch, mode, execution, enabled, expected):
    monkeypatch.setattr(application.settings, "workspace_mode", mode)
    monkeypatch.setattr(application.settings, "enable_workspace_execution", execution)
    monkeypatch.setattr(application.settings, "workspace_worker_enabled", enabled)
    monkeypatch.setattr(application.settings, "workspace_db_path", tmp_path / "workspace.sqlite3")
    monkeypatch.setitem(application._state, "pipeline", SimpleNamespace())
    assert "worker_supervisor" not in application._state
    async with application.workspace_worker_lifespan():
        assert ("worker_supervisor" in application._state) is expected
        if expected:
            pool = application._state["worker_supervisor"]
            assert pool.task_count == 2 and application._health_payload()["worker_ready"] is True
        assert (tmp_path / "workspace.sqlite3").exists() is (mode == "local")
    assert "worker_supervisor" not in application._state
    if expected:
        assert pool.task_count == pool.active_count == 0


@asynchronous
async def test_shutdown_during_pending_sqlite_claim_never_abandons_ownership(configured, monkeypatch):
    sdk, calls = configured
    import threading
    entered, release = threading.Event(), threading.Event()
    service = application._agent_durable_service()
    run = service.create(AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True),
                         idempotency_key="pending-claim")
    original = service.repository.claim_next_job
    def paused_claim(eligible):
        entered.set()
        assert release.wait(5)
        return original(eligible)
    monkeypatch.setattr(service.repository, "claim_next_job", paused_claim)
    pool, executor = worker(service, concurrency=1)
    await pool.start()
    assert await asyncio.to_thread(entered.wait, 5)
    stopping = asyncio.create_task(pool.stop())
    await pool._stop.wait()
    release.set()
    await asyncio.wait_for(stopping, 5)
    assert service.get(run.run_id).state == "interrupted"
    assert not sdk.requests and not calls and not executor.invocations
    assert pool.task_count == 0


@asynchronous
async def test_startup_executes_never_claimed_and_recovers_claimed_without_replay(configured, monkeypatch):
    sdk, calls = configured
    service = application._agent_durable_service()
    body = AgentRunCreateRequest(goal="Find evidence.", allow_decision_provider_execution=True)
    active = service.create(body, idempotency_key="restart-active")
    queued = service.create(body, idempotency_key="restart-queued")
    job_id = "job_" + active.run_id[6:]
    service.repository.transition_job(job_id, expected_revision=1, target_state="running")
    finished = asyncio.Event()
    class Observed(AgentJobExecutor):
        async def execute(self, job):
            await super().execute(job)
            finished.set()
    monkeypatch.setattr(application, "AgentJobExecutor", Observed)
    async with application.workspace_worker_lifespan():
        assert service.get(active.run_id).state == "interrupted"
        await asyncio.wait_for(finished.wait(), 5)
    assert service.get(queued.run_id).state == "succeeded"
    assert calls == ["read_document"] and len(sdk.requests) == 2
    assert "worker_supervisor" not in application._state


@asynchronous
async def test_real_pipeline_staging_and_evaluation_receipts_are_not_stolen(configured, tmp_path):
    from src.api.pipeline import PipelineService
    from src.api.pipeline_models import PipelineRunCreateRequest
    from tests.test_evaluation_jobs import _service, _create
    sdk, calls = configured
    service = application._agent_durable_service()
    pipeline = PipelineService(service.repository, application.settings)
    staged = pipeline.stage(PipelineRunCreateRequest(input_ids=["AAPL"], staging_profile="isolated"))
    evaluation, evaluation_calls = _service(tmp_path)
    evaluation_job = _create(evaluation)
    model_job = service.repository.create_job(namespace="model_test", job_type="runtime_identity",
        idempotency_key="model-test-staged", configuration_fingerprint="a" * 64, payload={}, steps=("identity",))
    pool, executor = worker(service)
    assert await pool._claim() is None
    await pool.start()
    await pool.stop()
    assert service.repository.get_job(staged.id).state == "queued"
    assert all(step.state == "pending" for step in service.repository.get_job(staged.id).steps)
    assert evaluation.get(evaluation_job.job_id)["budget_consumed"] == 0
    assert evaluation_calls == {"generation":0,"judging":0}
    assert service.repository.get_job(model_job.job_id).state == "queued"
    assert not sdk.requests and not calls and not executor.invocations
    # Its existing executor still owns exactly the same frozen case/attempt contract.
    evaluation.run(evaluation_job.job_id)
    result = evaluation.get(evaluation_job.job_id)
    assert result["state"] == "succeeded" and result["budget_consumed"] == 2
    assert evaluation_calls == {"generation":1,"judging":1}


@asynchronous
async def test_inflight_synchronous_tool_does_not_block_api_and_cancel_stops_new_work(configured, monkeypatch):
    import threading
    from src.agent.registry import build_tool_registry
    from tests.test_agent_orchestration import _services
    sdk, calls = configured
    entered, release = threading.Event(), threading.Event()
    services = _services(calls)
    original_catalog = services.catalog
    def blocked_catalog():
        entered.set()
        assert release.wait(5)
        return original_catalog()
    services.catalog = blocked_catalog
    monkeypatch.setattr(application, "create_agent_tool_registry", lambda: build_tool_registry(services))
    service = application._agent_durable_service()
    run = service.create(AgentRunCreateRequest(goal="Read evidence.", allow_decision_provider_execution=True),
                         idempotency_key="blocking-tool")
    pool, executor = worker(service)
    await pool.start()
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app),
                                    base_url="http://localhost:8000") as client:
            response = await asyncio.wait_for(client.get(f"/agent/runs/{run.run_id}",
                headers=_headers(token=BEARER)), 5)
        assert response.status_code == 200 and not release.is_set()
        current = service.get(run.run_id)
        assert service.cancel(run.run_id, expected_revision=current.revision).state == "cancelling"
        assert service.get(run.run_id).result is None
        release.set()
        await finish(pool, executor)
        assert service.get(run.run_id).state == "cancelled"
        assert len(sdk.requests) == 1 and calls == ["read_document"]
    finally:
        release.set()
        await pool.stop()
