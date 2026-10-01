"""Run established SCALE-001 invariants with OBS capture explicitly enabled."""
import asyncio

import pytest

from scripts.benchmarks.obs_001 import anchors, median_populations, trial
from scripts.benchmarks.scale_002_stats import Scenario, validate_report
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository
from src.workspace.worker import WorkerSupervisor
from tests import test_workspace_worker as existing


@pytest.mark.parametrize("name", [
    "test_start_stop_idle_wait_no_mutation_or_task_leak",
    "test_single_job_terminal_and_two_workers_one_invocation",
    "test_queued_cancel_no_execution_and_stale_revision",
    "test_shutdown_before_claim_preserves_queue_and_restart_executes",
    "test_grace_finishes_existing_owner_and_never_claims_next",
    "test_expired_grace_interrupts_uncertain_effect_and_no_replay",
    "test_executor_exception_is_sanitized_pool_survives",
    "test_nonterminal_executor_return_is_interrupted",
    "test_excluded_namespaces_and_unknown_type_stay_queued",
    "test_restart_preserves_queued_and_interrupts_claimed_crash_windows",
    "test_unexpected_worker_death_stops_claims_and_is_not_silent",
    "test_transient_claim_failure_waits_and_next_poll_recovers",
])
def test_existing_worker_invariants_with_capture(tmp_path, monkeypatch, caplog, name):
    database = WorkspaceDatabase(tmp_path / "enabled.sqlite3")
    database.initialize()
    repository = SQLiteJobRepository(database)
    original = WorkerSupervisor.__init__
    def enabled(self, *args, **kwargs):
        kwargs["attribution_enabled"] = True
        original(self, *args, **kwargs)
    monkeypatch.setattr(WorkerSupervisor, "__init__", enabled)
    function = getattr(existing, name)
    if "caplog" in function.__wrapped__.__code__.co_varnames:
        function(repository, caplog)
    else:
        function(repository)


@pytest.mark.integration
@pytest.mark.parametrize("profile", ["admission", "read", "research", "mixed", "sse"])
def test_obs_real_tcp_smoke_has_complete_bounded_content_free_phases(tmp_path, profile):
    scenario = Scenario(profile, concurrency=2, operations=4 if profile == "read" else 2, warmup=1, trials=1, latency_ms=5)
    result = asyncio.run(trial(scenario, tmp_path, 1, enabled=True))
    validate_report(result)
    data = result["attribution"]
    assert data["span_count"] > 0 and data["trace_count"] > 0
    assert data["missing_api"] == data["missing_workers"] == data["dropped"] == 0
    assert all(not value for value in result["correctness"]["counts"].values())
    assert result["correctness"]["database"]["schema"] == 7
    phases = {row["phase"] for row in data["phases"]}
    assert {"api.total", "api.access", "api.service_init"} <= phases
    if profile != "admission":
        assert "workspace.read" in phases
    else:
        # Admission reads stay inside its unchanged write transaction; expensive
        # initializer read connections are absent from the warm measured window.
        assert "workspace.read" not in phases
    if profile == "read":
        # Validated warm read factories no longer enter the writer/init boundary.
        assert "workspace.serialized_wait" not in phases and "workspace.initialize" not in phases
    else:
        assert "workspace.serialized_wait" in phases
    if profile != "read":
        assert "workspace.transaction" in phases
    if profile in ("research", "mixed", "sse"):
        assert {"worker.claim", "worker.service", "agent.provider", "agent.tool.search_documents", "agent.tool.read_document"} <= phases
    if profile in ("read", "research", "mixed"):
        assert "evaluation.compute" in phases
    if profile in ("mixed", "sse"):
        assert {"sse.send", "sse.serialize", "sse.read_events"} <= phases


def test_canonical_anchors_and_no_pooling_of_trial_percentiles():
    assert [(row.profile, row.concurrency, row.operations, row.latency_ms) for row in anchors()] == [
        ("admission", 50, 200, 0), ("read", 50, 200, 0), ("research", 10, 20, 0),
        ("research", 10, 20, 250), ("mixed", 25, 25, 250), ("sse", 25, 25, 250)]
    assert all(row.workers == 2 and row.trials == 3 and row.poll_ms == 500 for row in anchors())
    assert median_populations([dict(count=20, p50=value, p95=value, p99=None, max=value) for value in (1, 50, 100)]) == {
        "p50": 50, "p95": 50, "p99": None, "max": 50, "counts_per_trial": [20, 20, 20]}
