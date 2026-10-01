"""SCALE-002 CLI: bounded offline load characterization, not a production SLA."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from scripts.benchmarks.scale_002_stats import (
    PROTOCOL, PROFILES, Scenario, environment, lifecycle_durations, percentiles,
    summarize_trials, throughput, validate_report,
)


def git_binding() -> dict:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source = Path(__file__).parent
    digest = hashlib.sha256(b"".join((source / name).read_bytes() for name in (
        "scale_002.py", "scale_002_stats.py", "scale_002_runtime.py"))).hexdigest()
    committed = subprocess.run(["git", "ls-files", "--error-unmatch", *[
        f"scripts/benchmarks/{name}" for name in ("scale_002.py", "scale_002_stats.py", "scale_002_runtime.py")]],
        capture_output=True).returncode == 0
    return {"git_sha": sha, "harness_sha256": digest, "harness_committed": committed,
            "tracked_clean": not bool(subprocess.check_output(["git", "diff", "HEAD", "--name-only"], text=True).strip())}


def artifact_preflight() -> dict:
    # Defaults deliberately avoid .env, private paths and cloud credentials.
    index = Path("data/processed/qdrant")
    manifest = Path("data/processed/qdrant_index_manifest.json")
    return {"index_available": index.is_dir(), "manifest_available": manifest.is_file(),
            "local_source_available": Path("data/raw").is_dir()}


def artifact_binding() -> dict:
    manifest = Path("data/processed/qdrant_index_manifest.json")
    return {"manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None}


async def verify_jobs(bench, ids, expected, warmup_count):
    from src.agent.durable import _job_id
    from src.workspace.database import WorkspaceDatabase
    from src.workspace.jobs import SQLiteJobRepository, validate_job_transition
    observer = bench.observer
    repository = SQLiteJobRepository.from_settings(bench.application.settings)
    errors = Counter()
    terminal_counts = Counter()
    jobs = []
    if len(set(ids)) != len(ids): errors["duplicate_durable_id"] += 1
    for identifier in ids:
        job = await asyncio.to_thread(repository.get_job, _job_id(identifier))
        jobs.append(job)
        terminal_counts[job.state] += 1
        events = repository.list_agent_events(job.job_id)
        sequences = [event.sequence for event in events]
        if sequences != list(range(1, len(events) + 1)): errors["event_ordering"] += 1
        previous = "queued"
        for event in events:
            if event.state and event.state != previous:
                try: validate_job_transition(previous, event.state)
                except Exception: errors["invalid_lifecycle"] += 1
                previous = event.state
        if job.state in TERMINAL:
            if observer.owners[job.job_id] != (1 if job.started_at else 0): errors["duplicate_execution"] += 1
            if job.state == "succeeded":
                run = bench.application._agent_service_for_repository(repository).get(identifier)
                expected_calls = 3 if run.frozen.research else 2
                if observer.calls[job.job_id] != expected_calls: errors["duplicate_provider_execution"] += 1
                if run.result.decision_call_count != expected_calls: errors["decision_count_mismatch"] += 1
                if run.frozen.research and run.result.research.objectives[0].coverage != "sufficient":
                    errors["research_coverage"] += 1
            elif job.state == "cancelled" and not job.started_at and observer.calls[job.job_id]:
                errors["queued_cancel_executed"] += 1
            elif job.state == "cancelled" and job.started_at:
                run = bench.application._agent_service_for_repository(repository).get(identifier)
                if observer.calls[job.job_id] != 1 or run.result.tool_call_count != 0:
                    errors["inflight_cancel_executed_extra_work"] += 1
            elif job.state == "failed" and (job.job_id != bench.fail_job or observer.calls[job.job_id] != 1):
                errors["unexpected_failure_or_retry"] += 1
        elif job.state != "queued": errors["unexpected_active_job"] += 1
    if dict(terminal_counts) != expected: errors["terminal_status_mismatch"] += 1
    if observer.peak_active > bench.scenario.workers: errors["capacity_violation"] += 1
    for key in ("missing_events", "duplicate_events", "ordering_violations", "resume_failures", "connection_failures"):
        errors[key] += bench.sse[key]
    errors.update(observer.errors)
    # Reopen and inspect the same database after pool shutdown, not another empty DB.
    if bench.pool: await bench.pool.stop()
    database = WorkspaceDatabase(repository.database.path)
    version = await asyncio.to_thread(database.initialize)
    with database.connection() as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        count = connection.execute("SELECT COUNT(*) FROM jobs WHERE namespace='agent'").fetchone()[0]
        active = connection.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('running','cancelling')").fetchone()[0]
    errors["lost_jobs"] += abs(count - len(ids) - warmup_count)
    errors["database_issues"] += int(version != 7 or integrity != "ok" or active != 0)
    result = {name: errors[name] for name in ("lost_jobs", "duplicate_durable_id", "duplicate_execution",
        "duplicate_provider_execution", "decision_count_mismatch", "capacity_violation", "invalid_lifecycle",
        "event_ordering", "duplicate_claim", "duplicate_terminal", "queued_cancel_executed", "research_coverage",
        "terminal_status_mismatch", "database_issues", "sqlite_busy", "sqlite_error", "claim_failure",
        "inflight_cancel_executed_extra_work", "unexpected_failure_or_retry",
        "mutation_after_terminal",
        "unhealthy_pool", "missing_events", "duplicate_events", "ordering_violations", "resume_failures", "connection_failures")}
    if any(result.values()):
        raise BenchmarkFailure("correctness_gate_failed:" + ",".join(k for k, v in result.items() if v))
    return jobs, {"counts": result, "terminal_statuses": dict(terminal_counts),
                  "database": {"schema": version, "integrity": integrity, "job_count": count, "active_after_stop": active}}


# Lazy runtime import keeps statistic/report imports free of product startup.
from scripts.benchmarks.scale_002_runtime import BenchmarkFailure, TERMINAL, bounded_map, runtime


async def cancellation_workload(bench):
    from src.workspace.executors import AgentJobExecutor, ExecutorRegistry
    from src.workspace.jobs import SQLiteJobRepository
    from src.workspace.worker import WorkerConfig, WorkerSupervisor
    ids = await bounded_map(6, bench.scenario.concurrency, lambda i: bench.create(f"measured-{i}"))
    repository = SQLiteJobRepository.from_settings(bench.application.settings)
    pool = WorkerSupervisor(repository, ExecutorRegistry((AgentJobExecutor(
        lambda: bench.application._agent_service_for_repository(repository)),)), WorkerConfig(2, bench.scenario.poll_ms, 5000))
    bench.application._state["worker_supervisor"] = pool
    await pool.start()
    while len(bench.entered) < 2: await asyncio.sleep(.01)
    running = []
    queued = []
    for identifier in ids:
        run = (await bench.request("GET", f"/agent/runs/{identifier}")).json()
        (running if run["state"] == "running" else queued).append(run)
    for run in queued[-2:]:
        await bench.request("POST", f"/agent/runs/{run['run_id']}/cancel", headers={"If-Match": str(run["revision"])})
    chosen = running[0]
    await bench.request("POST", f"/agent/runs/{chosen['run_id']}/cancel", expected=409, headers={"If-Match": "1"})
    cancelled = (await bench.request("POST", f"/agent/runs/{chosen['run_id']}/cancel",
                                headers={"If-Match": str(chosen["revision"])})).json()
    if cancelled["state"] != "cancelling": raise BenchmarkFailure("inflight_cancel_not_cooperative")
    bench.release.set()
    await bench.wait_terminal(ids, idle=True)
    return ids


async def trial(scenario: Scenario, directory: Path, trial_index: int) -> dict:
    async with runtime(scenario, directory) as bench:
        warmup_ids = []
        if scenario.profile == "cancel":
            # Warm the exact API/DB/tool/model path with its production supervisor.
            from src.workspace.executors import AgentJobExecutor, ExecutorRegistry
            from src.workspace.jobs import SQLiteJobRepository
            from src.workspace.worker import WorkerConfig, WorkerSupervisor
            repository = SQLiteJobRepository.from_settings(bench.application.settings)
            pool = WorkerSupervisor(repository, ExecutorRegistry((AgentJobExecutor(
                lambda: bench.application._agent_service_for_repository(repository)),)), WorkerConfig(2, scenario.poll_ms, 5000))
            bench.application._state["worker_supervisor"] = pool
            await pool.start()
        warmup_ids = await bounded_map(scenario.warmup, min(scenario.concurrency, scenario.workers),
            lambda i: bench.create(f"warmup-{i}", scenario.profile in ("research", "sse", "mixed")))
        if scenario.profile != "admission":
            await bench.wait_terminal(warmup_ids, idle=True)
            for i in range(4): await bench.read(warmup_ids[0], i)
            if scenario.profile in ("sse", "mixed"): await bench.subscribe(warmup_ids[0])
        if scenario.profile == "cancel":
            await bench.pool.stop()
            bench.application._state.pop("worker_supervisor", None)
        bench.observer.reset()
        bench.request_ms.clear(); bench.statuses.clear(); bench.endpoint_ms.clear()
        bench.sse.clear(); bench.delivery_ms.clear(); bench.entered.clear()
        bench.measuring = True
        bench.observer.measuring = True
        started, cpu_started = time.perf_counter(), time.process_time()
        ids = []
        expected = {}

        async def work():
            nonlocal ids, expected
            if scenario.profile == "admission":
                ids = await bounded_map(scenario.operations, scenario.concurrency,
                                        lambda i: bench.create(f"measured-{i}"))
                expected = {"queued": len(ids)}
            elif scenario.profile == "read":
                await bounded_map(scenario.operations, scenario.concurrency,
                                  lambda i: bench.read(warmup_ids[0], i))
                expected = {}
            elif scenario.profile == "sse":
                ids = [await bench.create("measured-sse", True)]
                await bounded_map(scenario.operations, scenario.concurrency, lambda _i: bench.subscribe(ids[0]))
                await bench.wait_terminal(ids, idle=True)
                expected = {"succeeded": 1}
            elif scenario.profile == "cancel":
                ids = await cancellation_workload(bench)
                expected = {"succeeded": 3, "cancelled": 3}
            else:
                async def run(index):
                    identifier = await bench.create(f"measured-{index}", scenario.profile in ("research", "mixed"))
                    if scenario.profile == "mixed":
                        await bench.request("GET", "/agent/runs")
                        await bench.request("GET", f"/agent/runs/{identifier}")
                        await bench.subscribe(identifier)
                    await bench.wait_terminal([identifier])
                    if scenario.profile in ("research", "mixed"):
                        await bench.read(identifier, 2)
                        await bench.read(identifier, 3)
                    return identifier
                ids = await bounded_map(scenario.operations, scenario.concurrency, run)
                await bench.wait_terminal(ids, idle=True)
                expected = ({"failed": 1, "succeeded": len(ids) - 1} if scenario.profile == "degraded"
                            else {"succeeded": len(ids)})
        await asyncio.wait_for(work(), scenario.timeout_seconds)
        elapsed, cpu_seconds = time.perf_counter() - started, time.process_time() - cpu_started
        bench.measuring = False
        bench.observer.measuring = False
        jobs, correctness = await verify_jobs(bench, ids, expected, len(warmup_ids))
        queue, service, end_to_end = [], [], []
        for job in jobs:
            row = bench.observer.jobs[job.job_id]
            if "claimed" in row and "terminal" in row:
                q, s, e = lifecycle_durations(row["created"], row["claimed"], row["terminal"])
                queue.append(q); service.append(s); end_to_end.append(e)
        terminal_rows = [bench.observer.jobs[job.job_id] for job in jobs if job.state in TERMINAL]
        drain = (max(row["terminal"] for row in terminal_rows) - min(row["created"] for row in terminal_rows)
                 if terminal_rows else None)
        successes = sum(int(count) for status, count in bench.statuses.items() if int(status) < 400)
        result = {"status": "complete", "trial": trial_index, "operations": scenario.operations,
            "warmup_operations": scenario.warmup, "request_count": sum(bench.statuses.values()),
            "successes": successes, "failures": sum(bench.statuses.values()) - successes,
            "expected_rejections": bench.statuses["409"] if scenario.profile == "cancel" else 0,
            "unexpected_5xx": sum(count for code, count in bench.statuses.items() if int(code) >= 500),
            "status_distribution": dict(bench.statuses), "elapsed_seconds": elapsed,
            "requests_per_second": throughput(successes, elapsed),
            "jobs_per_second": throughput(sum(job.state == "succeeded" for job in jobs), drain) if drain else None,
            "drain_ms": drain * 1000 if drain is not None else None,
            "peak_active_workers": bench.observer.peak_active, "peak_queue_depth": bench.observer.peak_queue,
            "peak_worker_tasks_sampled": bench.peak_worker_tasks,
            "cpu_seconds": cpu_seconds, "cpu_core_equivalents": cpu_seconds / elapsed,
            "peak_rss_bytes": bench.peak_rss_bytes, "resource_scope": "combined_server_client_same_process",
            "sse": dict(bench.sse), "decision_calls": sum(bench.observer.calls.values()),
            "failure_injections": int(bench.fail_job is not None), "correctness": correctness,
            "endpoint_ms": {name: percentiles(values) for name, values in bench.endpoint_ms.items()}}
        for key, values in {"request_ms": bench.request_ms, "queue_wait_ms": queue,
            "service_ms": service, "end_to_end_ms": end_to_end, "claim_ms": bench.observer.claim_ms,
            "write_transaction_ms": bench.observer.transaction_ms, "write_lock_wait_ms": bench.observer.lock_wait_ms,
            "provider_ms": bench.observer.provider_ms, "tool_ms": bench.observer.tool_ms,
            "event_delivery_ms": bench.delivery_ms, "loop_lag_ms": bench.loop_lag_ms}.items():
            result[key] = percentiles(values)
        validate_report(result)
        return result


async def campaign(scenarios: list[Scenario], output: Path, max_seconds=1800) -> dict:
    binding = git_binding()
    report = {"protocol_version": PROTOCOL, **binding, "environment": environment(),
              "status": "incomplete", "scenarios": [], "skipped": []}
    began = time.perf_counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    def checkpoint():
        validate_report(report)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, allow_nan=False, indent=2), encoding="utf-8")
        os.replace(temporary, output)
    checkpoint()
    for index, scenario in enumerate(scenarios):
        if time.perf_counter() - began >= max_seconds:
            report["skipped"].extend({"scenario": item.binding(), "reason": "campaign_time_limit"}
                                     for item in scenarios[index:])
            checkpoint()
            return report
        item = {"config": scenario.binding(), "trials": [], "status": "incomplete"}
        if scenario.mode == "artifact": item["artifact_binding"] = artifact_binding()
        report["scenarios"].append(item)
        checkpoint()
        if scenario.mode == "artifact" and not all(artifact_preflight().values()):
            item.update(status="skipped", reason="local_artifact_prerequisites_unavailable",
                        preflight=artifact_preflight())
            checkpoint()
            continue
        for number in range(1, scenario.trials + 1):
            try:
                with tempfile.TemporaryDirectory(prefix="edqa-scale002-") as tmp:
                    result = await trial(scenario, Path(tmp), number)
            except Exception as error:
                item["failure_category"] = str(error) if isinstance(error, BenchmarkFailure) else type(error).__name__
                checkpoint()
                return report  # No escalation after unhealthy or nondeterministic evidence.
            item["trials"].append(result)
            checkpoint()
            print(f"profile={scenario.profile} clients={scenario.concurrency} workers={scenario.workers} "
                  f"synthetic_ms={scenario.latency_ms} trial={number} status=complete", flush=True)
        item.update(status="complete", summary=summarize_trials(item["trials"]))
        checkpoint()
    report["status"] = "complete"
    checkpoint()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="admission")
    parser.add_argument("--mode", choices=("hermetic", "artifact"), default="hermetic")
    parser.add_argument("--concurrency", default="1")
    parser.add_argument("--workers", default="2")
    parser.add_argument("--provider-latency-ms", default="0")
    parser.add_argument("--operations", type=int, default=20)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=4)
    parser.add_argument("--poll-ms", type=int, default=500)
    parser.add_argument("--max-campaign-seconds", type=int, default=1800)
    parser.add_argument("--output", type=Path, default=Path(".local/benchmarks/scale-002/report.json"))
    parser.add_argument("--artifact-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    # Refuse to overwrite tracked/user source or canonical corpus with result output.
    target = args.output.resolve()
    safe_root = Path(".local/benchmarks/scale-002").resolve()
    if safe_root not in target.parents or target.suffix != ".json":
        parser.error("output must be a JSON file under .local/benchmarks/scale-002")
    try:
        scenarios = [Scenario(args.profile, concurrency, workers, args.operations, latency,
                              args.trials, args.warmup, args.poll_ms, args.mode)
                     for latency in map(int, args.provider_latency_ms.split(","))
                     for workers in map(int, args.workers.split(","))
                     for concurrency in map(int, args.concurrency.split(","))]
        if not 1 <= args.max_campaign_seconds <= 7200 or len(scenarios) > 100:
            raise ValueError
    except ValueError:
        parser.error("invalid bounded benchmark configuration")
    if args.mode == "artifact" and not args.artifact_child:
        # Full local model startup is synchronous production code. An external
        # process deadline can stop it even if its event loop cannot tick.
        command = [sys.executable, "-m", "scripts.benchmarks.scale_002", *sys.argv[1:], "--artifact-child"]
        try:
            completed = subprocess.run(command, timeout=args.max_campaign_seconds + 120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            if args.output.exists():
                report = json.loads(args.output.read_text(encoding="utf-8"))
                report.update(status="incomplete", hard_deadline="artifact_process_wall_deadline")
                validate_report(report)
                args.output.write_text(json.dumps(report, allow_nan=False, indent=2), encoding="utf-8")
            raise SystemExit(1) from None
        raise SystemExit(completed.returncode)
    result = asyncio.run(campaign(scenarios, args.output, args.max_campaign_seconds))
    if result["status"] != "complete": raise SystemExit(1)


if __name__ == "__main__": main()
