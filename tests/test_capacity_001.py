"""Capacity evidence: valid interval partitions and fixed worker/provider bounds."""
import asyncio
from types import SimpleNamespace

import pytest

from scripts.benchmarks.capacity_001 import occupancy, points, select_completed, union_length
from scripts.benchmarks.scale_002_runtime import BenchmarkFailure
from src.agent.orchestration import AgentOrchestrator
from src.agent.policies import AgentExecutionContext, ToolPolicy
from src.agent.registry import build_tool_registry
from src.agent.state import AgentRunPolicy, TOOL_NAMES
from src.workspace.attribution import TimingSpan
from src.workspace.worker import WorkerConfig
from tests.test_agent_orchestration import _services
from tests.test_agent_provider import final, model, wire, FakeSDK
from tests.test_workspace_worker import (
    Executor, asynchronous, complete, pool, queued, repository,
)


def test_overlapping_nested_spans_partition_once_and_clip_to_service():
    def row(phase, start, stop):
        return TimingSpan(phase=phase, start_ns=start * 1_000_000,
                          end_ns=stop * 1_000_000, ordinal=1)
    trace = SimpleNamespace(dropped=0, records=[row("worker.service", 10, 110),
        row("agent.decision", 15, 50), row("agent.provider", 20, 40),
        row("agent.tool.ask_rag", 50, 80), row("generator.transport", 60, 70),
        row("workspace.transaction", 52, 58), row("agent.persist_result", 80, 100),
        row("workspace.critical_section", 85, 105), row("workspace.read", 0, 12)])
    result = occupancy(trace)
    assert result["provider"] == 30
    assert result["tools"] == 20
    assert result["persistence"] == 20
    assert result["workspace"] == 7
    assert result["unattributed"] == 23
    assert sum(result[k] for k in ("provider", "tools", "persistence", "workspace", "unattributed")) == 100
    assert result["agent.decision"] == 35 and result["agent.tool.ask_rag"] == 30
    assert union_length([(1, 4), (2, 3), (3, 6), (9, 11)]) == 7


@pytest.mark.parametrize("dropped,roots", [(1, 1), (0, 0), (0, 2)])
def test_incomplete_trace_cannot_claim_exclusive_occupancy(dropped, roots):
    row = TimingSpan(phase="worker.service", start_ns=0, end_ns=1, ordinal=1)
    with pytest.raises(BenchmarkFailure, match="incomplete_capacity_trace"):
        occupancy(SimpleNamespace(dropped=dropped, records=[row] * roots))


def test_matrix_covers_delays_workers_anchors_and_tool_controls():
    matrix = points()
    assert {(p.workers, p.delay_ms) for p in matrix if p.kind == "worker" and p.tool is None
            and p.provider_limit is None} == {(n, d) for n in (1, 2, 4, 8) for d in (0, 100, 250, 500)}
    assert {p.delay_ms for p in matrix if p.kind == "research"} == {0, 250, 500}
    assert {p.tool for p in matrix if p.tool} == {"inspect_retrieval", "ask_rag"}
    assert all(p.operations >= 20 for p in matrix)


def test_late_warmup_callback_cannot_enter_measured_durable_population():
    rows = {"warmup": {"service": 100}, "measured": {"service": 7}}
    telemetry = {"warmup": 9, "measured": 2}
    assert select_completed(rows, telemetry, ["measured"]) == ([{"service": 7}], [2])
    assert select_completed(rows, telemetry, []) == ([], [])
    for ids in (["missing"], ["measured", "measured"]):
        with pytest.raises(BenchmarkFailure, match="missing_capacity_workers"):
            select_completed(rows, telemetry, ids)
    with pytest.raises(BenchmarkFailure, match="missing_capacity_workers"):
        select_completed(rows, {}, ["measured"])


@pytest.mark.parametrize("value", [-1, 1000000, "many", None])
def test_additional_nonsensical_worker_configuration_fails_closed(value):
    with pytest.raises(ValueError):
        WorkerConfig(concurrency=value)


@pytest.mark.parametrize("workers", [1, 2, 4, 8])
@asynchronous
async def test_capacity_shutdown_queued_cancel_restart_no_replay(repository, workers):
    jobs = [queued(repository, "lifecycle-" + str(i)) for i in range(24)]
    cancelled = jobs[-1]
    repository.request_cancellation(cancelled.job_id, expected_revision=cancelled.revision)
    held = Executor(repository, block=True, target=workers)
    owner = pool(repository, held, concurrency=workers, grace=100)
    await owner.start()
    await asyncio.wait_for(held.entered.wait(), 10)
    assert owner.task_count == owner.active_count == held.maximum == workers
    claimed = set(held.calls)
    await owner.stop()
    assert owner.task_count == owner.active_count == held.active == 0
    assert len(claimed) == workers and cancelled.job_id not in claimed
    assert all(repository.get_job(identity).state == "interrupted" for identity in claimed)
    assert repository.get_job(cancelled.job_id).state == "cancelled"
    remaining = 23 - workers
    resumed = Executor(repository)
    fresh = pool(repository, resumed, concurrency=workers)
    await fresh.start()
    try:
        async def drained():
            while len(resumed.calls) < remaining or fresh.active_count:
                await asyncio.sleep(.01)
        await asyncio.wait_for(drained(), 15)
    finally:
        await fresh.stop()
    assert len(resumed.calls) == len(set(resumed.calls)) == remaining
    assert not claimed.intersection(resumed.calls) and cancelled.job_id not in resumed.calls
    with repository.database.connection() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.parametrize("workers", [1, 2, 4, 8])
@asynchronous
async def test_fixed_workers_naturally_bound_mocked_provider_with_large_backlog(repository, workers):
    release, entered, drained = asyncio.Event(), asyncio.Event(), asyncio.Event()
    active = peak = finished = 0
    jobs = [queued(repository, str(i)) for i in range(40)]
    calls = []

    async def transport(_request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == workers:
            entered.set()
        try:
            await release.wait()
            return wire(final())
        finally:
            active -= 1

    sdk = FakeSDK(*([transport] * len(jobs)))
    registry = build_tool_registry(_services(calls))

    class ProviderExecutor(Executor):
        async def execute(self, job):
            nonlocal finished
            self.calls.append(job.job_id)
            orchestrator = AgentOrchestrator(registry, model(sdk),
                policy=AgentRunPolicy(allow_decision_provider_execution=True, require_observation_for_final=False))
            result = await orchestrator.run("Summarize bounded evidence.",
                AgentExecutionContext(ToolPolicy(frozenset(TOOL_NAMES), False)))
            assert result.status == "completed"
            await asyncio.to_thread(complete, self.repository, job)
            finished += 1
            if finished == len(jobs):
                drained.set()

    executor = ProviderExecutor(repository)
    owner = pool(repository, executor, concurrency=workers)
    await owner.start()
    try:
        await asyncio.wait_for(entered.wait(), 10)
        assert owner.task_count == owner.active_count == active == peak == workers
        assert len(executor.calls) == workers
        assert len([t for t in asyncio.all_tasks() if t.get_name().startswith("durable-worker-")]) == workers
        release.set()
        await asyncio.wait_for(drained.wait(), 20)
    finally:
        release.set()
        await owner.stop()
    assert active == owner.active_count == owner.task_count == 0
    assert peak == workers and len(sdk.requests) == len(executor.calls) == len(set(executor.calls)) == 40
    assert not calls and all(options["max_retries"] == 0 for options in sdk.options)
    assert sdk.closed == 40
    for job in jobs:
        assert repository.get_job(job.job_id).state == "succeeded"
        events = repository.list_agent_events(job.job_id)
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    with repository.database.connection() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
