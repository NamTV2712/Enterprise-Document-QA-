"""SCALE-002 statistic/protocol and real offline benchmark correctness gates."""

import asyncio
import json
import math
from dataclasses import replace

import pytest

from scripts.benchmarks.scale_002 import artifact_preflight, campaign, trial
from scripts.benchmarks.scale_002_runtime import Observer, observe_database
from scripts.benchmarks.scale_002_stats import (
    Scenario, environment, lifecycle_durations, percentiles, summarize_trials,
    throughput, validate_report,
)


def test_percentiles_explicit_nearest_rank():
    result = percentiles(reversed(range(1, 101)))
    assert (result["p50"], result["p95"], result["p99"], result["max"]) == (50, 95, 99, 100)


@pytest.mark.parametrize("count,available", [(0, ()), (1, ()), (2, (50,)), (19, (50,)),
                                              (20, (50, 95)), (99, (50, 95)), (100, (50, 95, 99))])
def test_insufficient_samples_are_null(count, available):
    result = percentiles(range(count))
    for p in (50, 95, 99):
        assert (result[f"p{p}"] is not None) == (p in available)
        assert result[f"p{p}_status"] == ("available" if p in available else "insufficient_samples")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -1, True, "1"])
def test_nonfinite_and_invalid_samples_are_refused(value):
    with pytest.raises(ValueError): percentiles([value])


def test_throughput_zero_duration_and_explicit_units():
    assert throughput(200, 2) == 100
    assert throughput(0, 1) == 0
    assert throughput(20, 0) is None
    with pytest.raises(ValueError): throughput(-1, 2)
    with pytest.raises(ValueError): throughput(1, math.inf)


def test_monotonic_queue_service_end_to_end_relationship():
    q, s, e = lifecycle_durations(1, 1.2, 1.7)
    assert q == pytest.approx(200) and s == pytest.approx(500)
    assert e == pytest.approx(q + s)
    with pytest.raises(ValueError): lifecycle_durations(1, .9, 2)


@pytest.mark.parametrize("field,value", [("concurrency", 0), ("concurrency", 101), ("workers", 9),
    ("workers", True), ("operations", 1001), ("latency_ms", -1), ("latency_ms", 1001),
    ("trials", 0), ("warmup", 0), ("poll_ms", 99), ("mode", "live"), ("profile", "provider_stress")])
def test_configuration_bounds(field, value):
    with pytest.raises(ValueError): replace(Scenario("admission"), **{field: value})


def test_timeout_bound_and_binding():
    assert Scenario("research", operations=1000, workers=1, latency_ms=1000).timeout_seconds == 240
    binding = Scenario("research", latency_ms=250).binding()
    assert binding["percentile_minimum_samples"] == {"50": 2, "95": 20, "99": 100}
    assert binding["time_source"].startswith("time.perf_counter")
    assert binding["latency_ms"] == 250


@pytest.mark.parametrize("report", [{"foo": math.nan}, {"nested": [math.inf]}, {"hostname": "private"},
    {"nested": {"authorization": "fake"}}, {"value": "Bearer synthetic"}, {"value": "C:\\private\\file"}])
def test_report_refuses_nonfinite_sensitive_fields_and_paths(report):
    with pytest.raises(ValueError): validate_report(report)


def test_environment_whitelist_serializes_without_machine_identity():
    data = environment()
    assert set(data) == {"os_family", "os_version", "python", "sqlite", "logical_cpus", "ram_bytes",
                         "process_rss", "cpu", "runtime_versions"}
    assert data["logical_cpus"] >= 1
    validate_report(data)
    json.dumps(data, allow_nan=False)


def test_successful_commit_only_and_rollback_does_not_create_timings(tmp_path):
    from contextlib import ExitStack
    from src.workspace.database import WorkspaceDatabase
    from src.workspace.jobs import SQLiteJobRepository
    observer = Observer()
    path = (tmp_path / "workspace.sqlite3").resolve()
    with ExitStack() as stack:
        observe_database(stack, path, observer)
        database = WorkspaceDatabase(path); database.initialize()
        def fail(phase, _job_id):
            if phase == "after_create": raise RuntimeError("injected")
        repository = SQLiteJobRepository(database, failure_injector=fail, forbidden_secret_values=())
        with pytest.raises(RuntimeError):
            repository.create_job(namespace="agent", job_type="bounded_agent_run", idempotency_key="rollback",
                configuration_fingerprint="a" * 64, payload={}, steps=("execute_agent",))
        assert observer.jobs == {} and observer.events == {}


@pytest.mark.parametrize("profile", ["admission", "read", "worker", "research", "sse", "mixed", "cancel", "degraded"])
def test_real_http_offline_profile_smoke_and_warmup_exclusion(tmp_path, profile):
    count = 6 if profile == "cancel" else 2
    scenario = Scenario(profile, concurrency=2, workers=2, operations=count, latency_ms=0, trials=1, warmup=1)
    result = asyncio.run(trial(scenario, tmp_path, 1))
    assert result["status"] == "complete"
    assert not any(result["correctness"]["counts"].values())
    assert result["correctness"]["database"]["schema"] == 7
    assert result["correctness"]["database"]["integrity"] == "ok"
    assert result["correctness"]["database"]["job_count"] == 1 + (0 if profile == "read" else 1 if profile == "sse" else count)
    if profile == "admission":
        assert result["request_count"] == count and result["status_distribution"] == {"201": count}
        assert result["decision_calls"] == 0 and result["peak_active_workers"] == 0
    if profile == "read": assert result["request_count"] == count and result["decision_calls"] == 0
    if profile == "worker": assert result["decision_calls"] == count * 2
    if profile == "research": assert result["decision_calls"] == count * 3
    if profile == "sse": assert result["sse"]["successful_streams"] == count
    if profile == "cancel": assert result["expected_rejections"] == 1
    if profile == "degraded": assert result["failure_injections"] == 1 and result["decision_calls"] == 3
    validate_report(result)
    serialized = json.dumps(result, allow_nan=False)
    assert "SCALE002_SYNTHETIC" not in serialized and "Authorization" not in serialized


def test_trial_aggregation_keeps_boundaries_and_excludes_incomplete(tmp_path):
    result = asyncio.run(trial(Scenario("admission", operations=2, trials=1, warmup=1), tmp_path, 1))
    second = {**result, "trial": 2, "requests_per_second": result["requests_per_second"] * 3}
    summary = summarize_trials([result, second])
    assert summary["requests_per_second"] == pytest.approx(result["requests_per_second"] * 2)
    assert summary["request_ms"]["samples_per_trial"] == [2, 2]
    assert summary["request_ms"]["p99"] is None
    with pytest.raises(ValueError): summarize_trials([{**result, "status": "incomplete"}])


def test_artifact_missing_prerequisites_are_truthful_skip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not any(artifact_preflight().values())


def test_interrupted_campaign_never_summarizes_partial_trial(tmp_path, monkeypatch):
    from scripts.benchmarks import scale_002
    async def failure(*_args): raise asyncio.TimeoutError
    monkeypatch.setattr(scale_002, "trial", failure)
    result = asyncio.run(campaign([Scenario("admission", trials=3)], tmp_path / "out.json"))
    assert result["status"] == "incomplete"
    assert result["scenarios"][0]["status"] == "incomplete"
    assert "summary" not in result["scenarios"][0]
    assert json.loads((tmp_path / "out.json").read_text())["status"] == "incomplete"


def test_artifact_cli_external_deadline_keeps_result_incomplete(tmp_path, monkeypatch):
    import subprocess
    import sys
    from scripts.benchmarks.scale_002 import main
    monkeypatch.chdir(tmp_path)
    output = tmp_path / ".local/benchmarks/scale-002/deadline.json"
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps({"status": "incomplete", "scenarios": []}))
    monkeypatch.setattr(sys, "argv", ["scale002", "--mode", "artifact", "--max-campaign-seconds", "30",
                                    "--output", ".local/benchmarks/scale-002/deadline.json"])
    def stopped(command, **kwargs):
        assert kwargs["timeout"] == 150 and command[-1] == "--artifact-child"
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", stopped)
    with pytest.raises(SystemExit) as error: main()
    assert error.value.code == 1
    result = json.loads(output.read_text())
    assert result["status"] == "incomplete" and result["hard_deadline"] == "artifact_process_wall_deadline"
