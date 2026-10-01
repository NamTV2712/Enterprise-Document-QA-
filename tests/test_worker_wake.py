"""WORKER-002 hints never replace durable claims, permissions or lifecycle."""
import asyncio
import threading

import httpx
import pytest
from fastapi import FastAPI

from src.api.routers.agent_runs import create_agent_run_router
from src.workspace.executors import ExecutorRegistry
from src.workspace.jobs import JobConflictError
from src.workspace.worker import WorkerConfig, WorkerSupervisor
from tests.test_workspace_worker import repository, queued, Executor, asynchronous
from tests.test_agent_api import _local, _headers, BODY
from tests.test_agent_durable import _service
from tests.test_agent_orchestration import _final
from tests.test_agent_provider_api import configured


class IdleObserved(WorkerSupervisor):
    def __init__(self, repository, executor, *, concurrency=1):
        super().__init__(repository, ExecutorRegistry((executor,)), WorkerConfig(concurrency))
        self.idle_entered = asyncio.Event()
        self.idle_count = 0
        self.reasons = []
        self.claims = 0

    async def _claim(self):
        self.claims += 1
        return await super()._claim()

    async def _idle(self):
        self.idle_count += 1
        if self.idle_count == self.config.concurrency:
            self.idle_entered.set()
        try:
            reason = await super()._idle()
            self.reasons.append(reason)
            return reason
        finally:
            self.idle_count -= 1


@asynchronous
async def test_idle_hint_is_coalesced_fixed_state_and_claims_durable_row(repository):
    executor = Executor(repository)
    supervisor = IdleObserved(repository, executor, concurrency=2)
    assert not supervisor.notify_work()
    await supervisor.start()
    try:
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        tasks = set(asyncio.all_tasks())
        job = queued(repository)
        for _ in range(100):
            assert supervisor.notify_work()
        assert supervisor._wake.is_set()
        assert set(asyncio.all_tasks()) == tasks
        assert supervisor.task_count == 2
        await asyncio.wait_for(executor.finished.wait(), 5)
        assert executor.calls == [job.job_id]
        assert repository.get_job(job.job_id).state == "succeeded"
        assert "durable_admission_signal" in supervisor.reasons
        assert not supervisor._wake.is_set()
    finally:
        await supervisor.stop()
    assert not supervisor.notify_work() and supervisor.task_count == 0


@asynchronous
async def test_empty_hint_returns_to_bounded_poll_and_shutdown_wakes_sleepers(repository):
    supervisor = IdleObserved(repository, Executor(repository))
    await supervisor.start()
    await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
    supervisor.idle_entered.clear()
    assert supervisor.notify_work()
    await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
    # One additional authoritative check; the next idle wait has no pending hint.
    assert supervisor.claims == 2 and not supervisor._wake.is_set()
    await supervisor.stop()
    assert supervisor.reasons == ["durable_admission_signal", "shutdown"]
    assert not supervisor.notify_work()


@asynchronous
async def test_all_hints_lost_poll_finds_work_after_initial_empty_claim(repository):
    executor = Executor(repository)
    supervisor = IdleObserved(repository, executor)
    await supervisor.start()
    try:
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        job = queued(repository)
        # No notify call at all, including after the initial startup claim.
        await asyncio.wait_for(executor.finished.wait(), 5)
        assert executor.calls == [job.job_id]
        assert "poll_timeout" in supervisor.reasons
        assert repository.get_job(job.job_id).state == "succeeded"
    finally:
        await supervisor.stop()


@asynchronous
async def test_fresh_supervisor_discovers_preexisting_rows_without_hint(repository):
    old = IdleObserved(repository, Executor(repository))
    await old.start()
    await old.stop()
    job = queued(repository)
    executor = Executor(repository)
    fresh = IdleObserved(repository, executor)
    assert not fresh._wake.is_set()
    await fresh.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    await fresh.stop()
    assert executor.calls == [job.job_id]


@asynchronous
async def test_wrong_thread_and_loop_hints_rejected_without_event_mutation(repository):
    supervisor = IdleObserved(repository, Executor(repository))
    await supervisor.start()
    try:
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        assert not await asyncio.to_thread(supervisor.notify_work)
        async def foreign_loop():
            return supervisor.notify_work()
        assert not await asyncio.to_thread(lambda: asyncio.run(foreign_loop()))
        assert not supervisor._wake.is_set() and supervisor.claims == 1
    finally:
        await supervisor.stop()


@asynchronous
async def test_cancelled_and_ineligible_rows_cannot_execute_after_hint(repository):
    executor = Executor(repository)
    supervisor = IdleObserved(repository, executor)
    await supervisor.start()
    try:
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        cancelled = queued(repository)
        repository.request_cancellation(cancelled.job_id, expected_revision=1)
        excluded = queued(repository, "excluded", namespace="pipeline")
        unknown = queued(repository, "unknown", job_type="unregistered")
        supervisor.idle_entered.clear()
        assert supervisor.notify_work()
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        assert not executor.calls
        assert repository.get_job(cancelled.job_id).state == "cancelled"
        assert repository.get_job(excluded.job_id).state == "queued"
        assert repository.get_job(unknown.job_id).state == "queued"
        with pytest.raises(JobConflictError):
            repository.request_cancellation(cancelled.job_id, expected_revision=1)
    finally:
        await supervisor.stop()


@asynchronous
async def test_busy_owners_drain_eligible_backlog_in_existing_order(repository):
    executor = Executor(repository, block=True, target=2)
    supervisor = IdleObserved(repository, executor, concurrency=2)
    await supervisor.start()
    try:
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        first = [queued(repository, f"first-{i}") for i in range(2)]
        supervisor.notify_work()
        await asyncio.wait_for(executor.entered.wait(), 5)
        later = [queued(repository, f"later-{i}") for i in range(8)]
        for _ in later:
            supervisor.notify_work()
        assert supervisor.active_count == supervisor.task_count == 2
        assert len(executor.calls) == 2
        executor.release.set()
        supervisor.idle_entered.clear()
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        assert len(executor.calls) == len(set(executor.calls)) == 10
        assert executor.maximum == 2
        assert all(repository.get_job(j.job_id).state == "succeeded" for j in first + later)
        # With two claim threads, entry into execute need not preserve claim order;
        # authoritative running event revisions remain one per row.
        assert all(sum(e.state == "running" and e.event_type == "state_changed" for e in repository.list_events(j.job_id)) == 1 for j in first + later)
    finally:
        executor.release.set()
        await supervisor.stop()


@asynchronous
async def test_notification_follows_commit_on_http_loop_and_failure_keeps_row(tmp_path, monkeypatch, caplog):
    service, repository, *_ = _service(tmp_path, (_final("Bounded answer."),))
    _local(monkeypatch)
    app = FastAPI()
    loop, thread = asyncio.get_running_loop(), threading.get_ident()
    admitted = []
    def notify():
        assert asyncio.get_running_loop() is loop and threading.get_ident() == thread
        rows = repository.list_jobs().items
        assert len(rows) == 1 and rows[0].state == "queued"
        assert len(repository.list_events(rows[0].job_id)) == 1
        admitted.append(rows[0].job_id)
        raise RuntimeError("SYNTHETIC_NOTIFY_SECRET")
    app.include_router(create_agent_run_router(lambda: service, notify_work=notify))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        response = await client.post("/agent/runs", headers=_headers(), json=BODY)
        assert response.status_code == 201 and response.json()["state"] == "queued"
        assert len(admitted) == 1
        assert "SYNTHETIC_NOTIFY_SECRET" not in caplog.text + response.text
        bad = await client.post("/agent/runs", headers=_headers(), json={"goal":""})
        assert bad.status_code == 422 and len(admitted) == 1


@pytest.mark.parametrize("mode,execution,token,expected", [
    ("public", True, None, 404), ("local", False, None, 401),
    ("local", False, "valid", 403), ("local", True, None, 401),
])
@asynchronous
async def test_access_refusal_has_no_service_or_notifier_side_effect(monkeypatch, mode, execution, token, expected):
    from src.api import access
    from tests.test_agent_api import TOKEN
    _local(monkeypatch, execution=execution)
    monkeypatch.setattr(access.settings, "workspace_mode", mode)
    def forbidden():
        raise AssertionError("private composition reached")
    app = FastAPI()
    app.include_router(create_agent_run_router(forbidden, notify_work=forbidden))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        response = await client.post("/agent/runs", headers=_headers(token=TOKEN if token else None), json=BODY)
        assert response.status_code == expected


@asynchronous
async def test_application_lifespan_http_hint_real_agent_sse_and_terminal_replay(configured, monkeypatch):
    from src.api import app as application
    from tests.test_agent_provider import BEARER
    sdk, calls = configured
    monkeypatch.setattr(application.settings, "workspace_worker_enabled", True)
    monkeypatch.setattr(application.settings, "enable_performance_attribution", False)
    monkeypatch.delitem(application._state, "worker_supervisor", raising=False)
    idle, finished = asyncio.Event(), asyncio.Event()
    original_idle, original_execute, original_notify = WorkerSupervisor._idle, WorkerSupervisor._execute, WorkerSupervisor.notify_work
    notifications = []
    async def observed_idle(supervisor):
        idle.set()
        return await original_idle(supervisor)
    async def observed_execute(supervisor, job):
        try:
            return await original_execute(supervisor, job)
        finally:
            finished.set()
    def observed_notify(supervisor):
        assert asyncio.get_running_loop() is supervisor._loop
        assert supervisor.repository.list_jobs(state="queued").total == 1
        notifications.append(True)
        return original_notify(supervisor)
    monkeypatch.setattr(WorkerSupervisor, "_idle", observed_idle)
    monkeypatch.setattr(WorkerSupervisor, "_execute", observed_execute)
    monkeypatch.setattr(WorkerSupervisor, "notify_work", observed_notify)
    async with application.workspace_worker_lifespan():
        await asyncio.wait_for(idle.wait(), 5)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app), base_url="http://localhost:8000") as client:
            headers = _headers(token=BEARER)
            body = {"goal":"Find relevant risk evidence.", "allow_decision_provider_execution":True}
            created = await client.post("/agent/runs", headers=headers, json=body)
            assert created.status_code == 201 and notifications == [True]
            await asyncio.wait_for(finished.wait(), 5)
            run_id = created.json()["run_id"]
            detail = await client.get(f"/agent/runs/{run_id}", headers=headers)
            assert detail.json()["state"] == "succeeded"
            events = await client.get(f"/agent/runs/{run_id}/events", headers=headers)
            sequences = [int(line[4:]) for line in events.text.splitlines() if line.startswith("id: ")]
            assert sequences == list(range(1, len(sequences) + 1))
            resumed = await client.get(f"/agent/runs/{run_id}/events", headers={**headers,"Last-Event-ID":"2"})
            assert "id: 1\n" not in resumed.text and "id: 2\n" not in resumed.text
            replay = await client.post("/agent/runs", headers=headers, json=body)
            assert replay.json()["run_id"] == run_id and notifications == [True]
            assert len(sdk.requests) == 2 and calls == ["read_document"]
    assert "worker_supervisor" not in application._state


@asynchronous
async def test_application_workers_disabled_admission_stays_queued(configured, monkeypatch):
    from src.api import app as application
    from tests.test_agent_provider import BEARER
    sdk, calls = configured
    monkeypatch.setattr(application.settings, "workspace_worker_enabled", False)
    monkeypatch.delitem(application._state, "worker_supervisor", raising=False)
    async with application.workspace_worker_lifespan():
        assert "worker_supervisor" not in application._state
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app), base_url="http://localhost:8000") as client:
            response = await client.post("/agent/runs", headers=_headers(token=BEARER), json=BODY)
            assert response.status_code == 201 and response.json()["state"] == "queued"
            assert application._agent_durable_service().get(response.json()["run_id"]).state == "queued"
            assert not sdk.requests and not calls


@asynchronous
async def test_releasing_one_owner_claims_oldest_eligible_and_keeps_capacity(repository):
    from tests.test_workspace_worker import complete
    release_one, release_two, both, later_done = (asyncio.Event() for _ in range(4))
    calls = []
    class Controlled(Executor):
        async def execute(self, job):
            calls.append(job.job_id)
            position = len(calls)
            if position == 2:
                both.set()
            if position <= 2:
                await (release_one if position == 1 else release_two).wait()
            await asyncio.to_thread(complete, repository, job)
            if position == 6:
                later_done.set()
    supervisor = IdleObserved(repository, Controlled(repository), concurrency=2)
    await supervisor.start()
    try:
        await asyncio.wait_for(supervisor.idle_entered.wait(), 5)
        for i in range(2):
            queued(repository, f"owner-{i}")
        supervisor.notify_work()
        await asyncio.wait_for(both.wait(), 5)
        later = [queued(repository, f"backlog-{i}") for i in range(4)]
        expected = [j.job_id for j in sorted(later, key=lambda j:(j.created_at,j.job_id))]
        supervisor.notify_work()
        assert supervisor.active_count == 2 and repository.list_jobs(state="queued").total == 4
        release_one.set()
        await asyncio.wait_for(later_done.wait(), 5)
        assert calls[2:] == expected and not release_two.is_set()
        assert supervisor.task_count == 2
    finally:
        release_one.set()
        release_two.set()
        await supervisor.stop()


@asynchronous
async def test_http_admission_reads_sse_and_worker_writes_progress_at_barrier(configured, monkeypatch):
    import sqlite3
    from src.api import app as application
    from src.workspace.database import WorkspaceDatabase
    from tests.test_agent_provider import BEARER
    from tests.test_agent_worker import worker
    sdk, calls = configured
    service = application._agent_durable_service()
    inserted, release = threading.Event(), threading.Event()
    original = WorkspaceDatabase._open_connection
    class Paused(sqlite3.Connection):
        def execute(self, sql, *args):
            result = super().execute(sql, *args)
            if sql.startswith("INSERT INTO job_events(") and "'agent_decision'" in sql and not inserted.is_set():
                inserted.set()
                assert release.wait(10)
            return result
    def connect(*args, **kwargs):
        return original(*args, **kwargs, factory=Paused)
    monkeypatch.setattr(WorkspaceDatabase, "_open_connection", staticmethod(connect))
    supervisor, executor = worker(service, concurrency=1)
    monkeypatch.setitem(application._state, "worker_supervisor", supervisor)
    await supervisor.start()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app), base_url="http://localhost:8000") as client:
            headers = _headers(token=BEARER)
            first = await client.post("/agent/runs", headers=headers, json={
                "goal":"Find risk evidence.","allow_decision_provider_execution":True})
            assert first.status_code == 201
            run_id = first.json()["run_id"]
            assert await asyncio.to_thread(inserted.wait, 5)
            async def admission(i):
                return await client.post("/agent/runs", headers={**headers,"Idempotency-Key":f"fairness-{i}"}, json=BODY)
            pending = [asyncio.create_task(admission(i)) for i in range(5)]
            async def read(endpoint):
                response = await client.get(endpoint, headers=headers)
                assert response.status_code == 200
                return response
            responses = await asyncio.wait_for(asyncio.gather(*(read(p) for p in (
                "/agent/runs", f"/agent/runs/{run_id}", f"/agent/runs/{run_id}/results", f"/agent/runs/{run_id}/events"))), 5)
            assert "event: agent_decision" not in responses[-1].text
            assert not executor.finished.is_set()
            release.set()
            accepted = await asyncio.wait_for(asyncio.gather(*pending), 5)
            assert all(r.status_code == 201 for r in accepted)
            identifiers = [run_id] + [r.json()["run_id"] for r in accepted]
            async def terminal():
                while any(service.get(i).state not in {"succeeded","failed"} for i in identifiers):
                    await asyncio.sleep(.01)
            await asyncio.wait_for(terminal(), 10)
            assert service.get(run_id).state == "succeeded"
            assert len(executor.invocations) == len(set(executor.invocations)) == 6
            assert len(sdk.requests) == 2 and calls == ["read_document"]
            for identifier in identifiers:
                events = await read(f"/agent/runs/{identifier}/events")
                seq = [int(line[4:]) for line in events.text.splitlines() if line.startswith("id: ")]
                assert seq == list(range(1, len(seq) + 1))
    finally:
        release.set()
        await supervisor.stop()
