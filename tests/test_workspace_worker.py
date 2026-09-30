"""SCALE-001 ownership, task bounds and lifecycle; no external transport."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import wraps
import json
import threading

import pytest

from src.workspace.database import WorkspaceDatabase
from src.workspace.executors import AgentJobExecutor, ExecutorRegistry
from src.workspace.jobs import JobConflictError, SQLiteJobRepository
from src.workspace.worker import WorkerConfig, WorkerSupervisor


def asynchronous(test):
    @wraps(test)
    def exercise(*args, **kwargs):
        return asyncio.run(test(*args, **kwargs))
    return exercise


@pytest.fixture
def repository(tmp_path):
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    assert db.initialize() == 7
    return SQLiteJobRepository(db)


def queued(repository, key="first", *, namespace="agent", job_type="synthetic_worker"):
    return repository.create_job(namespace=namespace, job_type=job_type,
        idempotency_key=key, configuration_fingerprint="a" * 64, payload={}, steps=("execute",))


def complete(repository, job):
    current = repository.get_job(job.job_id)
    if current.state == "cancelling":
        return repository.acknowledge_cancellation(job.job_id, expected_revision=current.revision)
    current = repository.transition_step(job.job_id, current.steps[0].step_id,
        expected_job_revision=current.revision, expected_step_revision=current.steps[0].revision,
        target_state="running")
    current = repository.transition_step(job.job_id, current.steps[0].step_id,
        expected_job_revision=current.revision, expected_step_revision=current.steps[0].revision,
        target_state="succeeded")
    return repository.transition_job(job.job_id, expected_revision=current.revision,
                                    target_state="succeeded", result={"completed": True})


class Executor:
    namespace = "agent"
    job_type = "synthetic_worker"

    def __init__(self, repository, *, block=False, target=1):
        self.repository = repository
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        if not block:
            self.release.set()
        self.finished = asyncio.Event()
        self.target = target
        self.calls = []
        self.active = 0
        self.maximum = 0

    async def execute(self, job):
        self.calls.append(job.job_id)
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        if self.active == self.target:
            self.entered.set()
        try:
            await self.release.wait()
            await asyncio.to_thread(complete, self.repository, job)
        finally:
            self.active -= 1
            self.finished.set()


def pool(repository, executor, *, concurrency=1, grace=1000):
    return WorkerSupervisor(repository, ExecutorRegistry((executor,)),
                            WorkerConfig(concurrency, 500, grace))


@pytest.mark.parametrize("field,value", [
    ("concurrency", 0), ("concurrency", 17), ("concurrency", True), ("concurrency", 1.5),
    ("poll_interval_ms", 99), ("poll_interval_ms", 5001), ("poll_interval_ms", False),
    ("shutdown_grace_ms", 99), ("shutdown_grace_ms", 60001), ("shutdown_grace_ms", True),
])
def test_config_hard_bounds(field, value):
    with pytest.raises(ValueError):
        WorkerConfig(**{field: value})


def test_registry_is_exact_closed_and_unique(repository):
    executor = Executor(repository)
    registry = ExecutorRegistry((executor,))
    job = queued(repository)
    assert registry.resolve(job) is executor
    for changed in (replace(job, namespace="pipeline"), replace(job, job_type="not_registered"),
                    replace(job, namespace="module_name")):
        with pytest.raises(ValueError, match="no registered"):
            registry.resolve(changed)
    for entries in ((), (executor, executor)):
        with pytest.raises(ValueError):
            ExecutorRegistry(entries)
    executor.namespace = "arbitrary_module"
    with pytest.raises(ValueError):
        ExecutorRegistry((executor,))


def test_claim_order_ties_are_stable_and_existing_index_is_used(repository):
    repository._clock = lambda: "2026-09-30T00:00:00Z"
    jobs = [queued(repository, str(index)) for index in range(4)]
    claimed = [repository.claim_next_job((("agent", "synthetic_worker"),)) for _ in jobs]
    assert [job.job_id for job in claimed] == sorted(job.job_id for job in jobs)
    assert all(job.state == "running" and job.revision == 2 for job in claimed)
    assert repository.claim_next_job((("agent", "synthetic_worker"),)) is None
    with repository.database.connection() as connection:
        plan = list(connection.execute("EXPLAIN QUERY PLAN SELECT job_id FROM jobs "
            "WHERE namespace='agent' AND state='queued' AND job_type='synthetic_worker' "
            "ORDER BY created_at,job_id LIMIT 1"))
    assert any("jobs_listing_idx" in row[3] for row in plan)
    assert not any("SCAN jobs" in row[3] for row in plan)


def test_claim_transaction_race_two_repositories_one_owner(repository):
    job = queued(repository)
    barrier = threading.Barrier(2)
    def claim():
        other = SQLiteJobRepository(WorkspaceDatabase(repository.database.path))
        barrier.wait(timeout=5)
        return other.claim_next_job((("agent", "synthetic_worker"),))
    with ThreadPoolExecutor(max_workers=2) as threads:
        results = list(threads.map(lambda _: claim(), range(2)))
    assert len([result for result in results if result]) == 1
    assert repository.get_job(job.job_id).revision == 2
    assert [event.state for event in repository.list_events(job.job_id)] == ["queued", "running"]


def test_claim_and_event_rollback_together(repository):
    job = queued(repository)
    repository._failure_injector = lambda phase, _id: (
        (_ for _ in ()).throw(RuntimeError("synthetic")) if phase == "after_job_update" else None)
    with pytest.raises(RuntimeError):
        repository.claim_next_job((("agent", "synthetic_worker"),))
    assert repository.get_job(job.job_id).state == "queued"
    assert len(repository.list_events(job.job_id)) == 1


@asynchronous
async def test_start_stop_idle_wait_no_mutation_or_task_leak(repository):
    class IdlePool(WorkerSupervisor):
        def __init__(self, *args):
            super().__init__(*args)
            self.waiters = 0
            self.idle = asyncio.Event()
        async def _idle(self):
            self.waiters += 1
            if self.waiters == self.config.concurrency:
                self.idle.set()
            await self._stop.wait()
    executor = Executor(repository)
    supervisor = IdlePool(repository, ExecutorRegistry((executor,)), WorkerConfig(2))
    await supervisor.start()
    assert supervisor.task_count == 2
    await asyncio.wait_for(supervisor.idle.wait(), 5)
    assert supervisor.healthy and supervisor.waiters == 2 and not executor.calls
    assert repository.list_jobs().total == 0
    await supervisor.stop()
    assert supervisor.task_count == supervisor.active_count == 0
    assert not [t for t in asyncio.all_tasks() if t.get_name().startswith("durable-worker-")]
    await supervisor.start()
    await supervisor.stop()
    await supervisor.stop()


@pytest.mark.parametrize("count", [4, 80])
@asynchronous
async def test_capacity_and_backpressure_fixed_two_tasks(repository, count):
    jobs = [queued(repository, str(index)) for index in range(count)]
    executor = Executor(repository, block=True, target=2)
    supervisor = pool(repository, executor, concurrency=2)
    await supervisor.start()
    await asyncio.wait_for(executor.entered.wait(), 5)
    assert supervisor.active_count == executor.maximum == 2
    assert supervisor.task_count == 2 and len(executor.calls) == 2
    assert repository.list_jobs(state="queued").total == count - 2
    tasks = [t for t in asyncio.all_tasks() if t.get_name().startswith("durable-worker-")]
    assert len(tasks) == 2
    executor.release.set()
    # Stop grants existing owners grace, and leaves the durable backlog queued.
    await supervisor.stop()
    assert executor.maximum == 2 and supervisor.task_count == 0
    assert all(repository.get_job(job.job_id).state in {"queued", "succeeded"} for job in jobs)


@asynchronous
async def test_single_job_terminal_and_two_workers_one_invocation(repository):
    job = queued(repository)
    executor = Executor(repository)
    supervisor = pool(repository, executor, concurrency=2)
    await supervisor.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    await supervisor.stop()
    final = repository.get_job(job.job_id)
    assert final.state == "succeeded" and final.result == {"completed": True}
    assert executor.calls == [job.job_id]
    sequences = [event.sequence for event in repository.list_events(job.job_id)]
    assert sequences == list(range(1, len(sequences) + 1))


@asynchronous
async def test_queued_cancel_no_execution_and_stale_revision(repository):
    job = queued(repository)
    cancelled = repository.request_cancellation(job.job_id, expected_revision=1)
    assert cancelled.state == "cancelled"
    with pytest.raises(JobConflictError):
        repository.request_cancellation(job.job_id, expected_revision=1)
    executor = Executor(repository)
    supervisor = pool(repository, executor)
    await supervisor.start()
    assert await supervisor._claim() is None
    await supervisor.stop()
    assert not executor.calls and repository.get_job(job.job_id).state == "cancelled"


@asynchronous
async def test_shutdown_before_claim_preserves_queue_and_restart_executes(repository):
    job = queued(repository)
    executor = Executor(repository)
    supervisor = pool(repository, executor)
    await supervisor.start()
    await supervisor.stop()  # No event-loop yield before stop signal.
    assert repository.get_job(job.job_id).state == "queued" and not executor.calls
    await supervisor.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    await supervisor.stop()
    assert repository.get_job(job.job_id).state == "succeeded"


@asynchronous
async def test_grace_finishes_existing_owner_and_never_claims_next(repository):
    first = queued(repository)
    executor = Executor(repository, block=True)
    supervisor = pool(repository, executor)
    await supervisor.start()
    await asyncio.wait_for(executor.entered.wait(), 5)
    next_job = queued(repository, "next")
    stopping = asyncio.create_task(supervisor.stop())
    await supervisor._stop.wait()
    assert not stopping.done()
    executor.release.set()
    await asyncio.wait_for(stopping, 5)
    assert repository.get_job(first.job_id).state == "succeeded"
    assert repository.get_job(next_job.job_id).state == "queued"
    assert executor.calls == [first.job_id]


@asynchronous
async def test_expired_grace_interrupts_uncertain_effect_and_no_replay(repository):
    job = queued(repository)
    executor = Executor(repository, block=True)
    supervisor = pool(repository, executor, grace=100)
    await supervisor.start()
    await asyncio.wait_for(executor.entered.wait(), 5)
    current = repository.get_job(job.job_id)
    repository.request_cancellation(job.job_id, expected_revision=current.revision)
    await asyncio.wait_for(supervisor.stop(), 5)
    final = repository.get_job(job.job_id)
    assert final.state == "interrupted" and final.failure_code == "worker_interrupted"
    assert final.result is None and supervisor.task_count == supervisor.active_count == 0
    await supervisor.start()
    await supervisor.stop()
    assert executor.calls == [job.job_id]


@asynchronous
async def test_executor_exception_is_sanitized_pool_survives(repository, caplog):
    first = queued(repository)
    class Throwing(Executor):
        async def execute(self, job):
            if job.job_id == first.job_id:
                raise RuntimeError("SYNTHETIC_PRIVATE_PAYLOAD_79A6")
            await super().execute(job)
    executor = Throwing(repository)
    second = queued(repository, "second")
    with repository.database.transaction(write=True) as connection:
        connection.execute("UPDATE jobs SET created_at='2020-01-01' WHERE job_id=?", (first.job_id,))
    supervisor = pool(repository, executor)
    await supervisor.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    assert supervisor.healthy
    await supervisor.stop()
    assert repository.get_job(first.job_id).state == "interrupted"
    assert repository.get_job(second.job_id).state == "succeeded"
    surfaces = json.dumps(repository.get_job(first.job_id).__dict__, default=str) + caplog.text
    assert "SYNTHETIC_PRIVATE_PAYLOAD_79A6" not in surfaces


@asynchronous
async def test_nonterminal_executor_return_is_interrupted(repository):
    job = queued(repository)
    class Incomplete(Executor):
        async def execute(self, _job):
            self.finished.set()
    executor = Incomplete(repository)
    supervisor = pool(repository, executor)
    await supervisor.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    await supervisor.stop()
    assert repository.get_job(job.job_id).state == "interrupted"


@asynchronous
async def test_excluded_namespaces_and_unknown_type_stay_queued(repository):
    excluded = [queued(repository, namespace=name) for name in ("pipeline", "evaluation", "model_test")]
    excluded.append(queued(repository, "unknown", job_type="arbitrary_module"))
    executor = Executor(repository)
    supervisor = pool(repository, executor)
    assert await supervisor._claim() is None
    assert all(repository.get_job(job.job_id).state == "queued" for job in excluded)
    assert not executor.calls


@asynchronous
async def test_restart_preserves_queued_and_interrupts_claimed_crash_windows(repository):
    before_call = queued(repository)
    after_effect = queued(repository, "after-effect")
    never_claimed = queued(repository, "never-claimed")
    for job in (before_call, after_effect):
        repository.transition_job(job.job_id, expected_revision=1, target_state="running")
    assert len(repository.recover_interrupted_jobs()) == 2
    executor = Executor(repository)
    reopened = SQLiteJobRepository(WorkspaceDatabase(repository.database.path))
    assert reopened.database.initialize() == 7
    supervisor = pool(reopened, executor)
    await supervisor.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    await supervisor.stop()
    assert executor.calls == [never_claimed.job_id]
    assert all(reopened.get_job(job.job_id).state == "interrupted" for job in (before_call, after_effect))


@asynchronous
async def test_unexpected_worker_death_stops_claims_and_is_not_silent(repository, caplog):
    class Dying(WorkerSupervisor):
        async def _worker(self):
            raise RuntimeError("DO_NOT_EXPOSE_EXCEPTION")
    supervisor = Dying(repository, ExecutorRegistry((Executor(repository),)), WorkerConfig(1))
    await supervisor.start()
    await asyncio.wait_for(supervisor._stop.wait(), 5)
    assert not supervisor.healthy
    await supervisor.stop()
    assert "durable_worker_stopped_unexpectedly" in caplog.text
    assert "DO_NOT_EXPOSE_EXCEPTION" not in caplog.text


@asynchronous
async def test_transient_claim_failure_waits_and_next_poll_recovers(repository, caplog):
    job = queued(repository)
    original = repository.claim_next_job
    attempts = []
    def claim(eligible):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("SYNTHETIC_PRIVATE_DATABASE_ERROR")
        return original(eligible)
    repository.claim_next_job = claim
    executor = Executor(repository)
    class Waiting(WorkerSupervisor):
        async def _idle(self):
            assert len(attempts) == 1
            await super()._idle()
    supervisor = Waiting(repository, ExecutorRegistry((executor,)), WorkerConfig(1))
    await supervisor.start()
    await asyncio.wait_for(executor.finished.wait(), 5)
    await supervisor.stop()
    assert repository.get_job(job.job_id).state == "succeeded"
    assert "durable_worker_claim_failed" in caplog.text
    assert "SYNTHETIC_PRIVATE_DATABASE_ERROR" not in caplog.text
