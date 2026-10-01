"""Fixed OBS-001 attribution campaign over the unchanged SCALE-002 workloads."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics as stdstats
import subprocess
import tempfile
import time
from dataclasses import asdict
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from scripts.benchmarks import scale_002 as scale
from scripts.benchmarks import scale_002_runtime as runtime_module
from scripts.benchmarks.scale_002_stats import Scenario, environment, summarize_trials, validate_report
from src.workspace.attribution import PROTOCOL, statistics

MAX_TRIAL_TRACES = 4096
MAX_TRIAL_SPANS = 65536


class ObservedScenario(Scenario):
    @property
    def timeout_seconds(self):
        return min(240.0, max(120.0, super().timeout_seconds))


async def trial(scenario: Scenario, directory: Path, index: int, *, enabled=True):
    """Production capture/sink, real loopback TCP, synthetic provider only."""
    from src.api import app as application
    from src.api.telemetry import RequestTelemetry
    if not isinstance(scenario, ObservedScenario):
        scenario = ObservedScenario(**asdict(scenario))
    clients, traces, worker_ids = {}, {}, set()
    span_count = 0
    original_runtime = scale.runtime
    original_hook = RequestTelemetry.record_attribution

    def response(bench, correlation, category, duration):
        if len(clients) >= MAX_TRIAL_TRACES or correlation in clients or not correlation:
            raise runtime_module.BenchmarkFailure("client_correlation_budget_or_identity")
        clients[correlation] = (category, duration)

    def completed(trace, *, correlation_id, route_template, persisted=False):
        nonlocal span_count
        original_hook(application.telemetry, trace, correlation_id=correlation_id, route_template=route_template, persisted=persisted)
        if correlation_id in traces or len(traces) >= MAX_TRIAL_TRACES or span_count + len(trace.records) > MAX_TRIAL_SPANS:
            raise runtime_module.BenchmarkFailure("trace_budget_or_identity")
        span_count += len(trace.records)
        traces[correlation_id] = (trace.summary(), tuple(trace.records), route_template, persisted)

    @asynccontextmanager
    async def observed_runtime(configuration, destination):
        async with original_runtime(configuration, destination) as bench:
            yield bench
            worker_ids.update(bench.observer.jobs)

    with patch.object(application.settings, "enable_performance_attribution", enabled), \
         patch.object(runtime_module.Runtime, "observe_response", response), \
         patch.object(application.telemetry, "record_attribution", completed), \
         patch.object(scale, "runtime", observed_runtime):
        result = await scale.trial(scenario, directory, index)
    groups = defaultdict(list)
    outcomes = defaultdict(Counter)
    server, differences, remainder = defaultdict(list), defaultdict(list), defaultdict(list)
    accepted = [identity for identity in traces if identity in clients or identity in worker_ids]
    for identity in accepted:
        summary, records, route, _persisted = traces[identity]
        for record in records:
            key = (summary.source, route, record.phase, record.operation)
            groups[key].append(record.duration_ms)
            outcomes[key][record.outcome] += 1
        if identity in clients:
            category, client_ms = clients[identity]
            roots = [row.duration_ms for row in records if row.phase == "api.total"]
            if len(roots) != 1:
                raise runtime_module.BenchmarkFailure("server_total_missing")
            server[category].append(roots[0])
            differences[category].append(client_ms - roots[0])
            if summary.remainder_ms is not None:
                remainder[category].append(summary.remainder_ms)
    missing = len(set(clients) - set(traces)) if enabled else 0
    dropped = sum(traces[identity][0].dropped for identity in accepted)
    expected_workers = result["correctness"]["terminal_statuses"].get("succeeded", 0)
    missing_workers = expected_workers - len(set(worker_ids) & set(traces)) if enabled else 0
    if missing or missing_workers or dropped:
        raise runtime_module.BenchmarkFailure("attribution_completeness_gate")
    result["attribution"] = {"enabled": enabled, "protocol": PROTOCOL,
        "population": "individual_inclusive_spans_within_one_trial",
        "trace_count": len(accepted), "span_count": sum(len(traces[key][1]) for key in accepted),
        "summary_bytes": sum(len(traces[key][0].model_dump_json().encode()) for key in accepted),
        "persisted_count": sum(traces[key][3] for key in accepted),
        "persisted_summary_bytes": sum(len(traces[key][0].model_dump_json().encode()) for key in accepted if traces[key][3]),
        "dropped": dropped, "missing_api": missing, "missing_workers": missing_workers,
        "server_ms": {key: statistics(values) for key, values in sorted(server.items())},
        "client_observed_minus_server_ms": {key: statistics(values, signed=True) for key, values in sorted(differences.items())},
        "server_remainder_ms": {key: statistics(values) for key, values in sorted(remainder.items())},
        "phases": [{"source": source, "route_template": route, "phase": phase, "operation": operation,
                    "duration_ms": statistics(values), "outcomes": dict(outcomes[source, route, phase, operation])}
                   for (source, route, phase, operation), values in sorted(groups.items())]}
    validate_report(result)
    return result


def median_populations(values):
    return {key: stdstats.median([value[key] for value in values])
            if all(value[key] is not None for value in values) else None for key in ("p50", "p95", "p99", "max")} | {
            "counts_per_trial": [value["count"] for value in values]}


def summarize(trials):
    result = summarize_trials(trials)
    attribution = [value["attribution"] for value in trials]
    result["attribution"] = {"protocol": PROTOCOL, "enabled": attribution[0]["enabled"],
        "trace_counts": [value["trace_count"] for value in attribution],
        "span_counts": [value["span_count"] for value in attribution],
        "summary_bytes": [value["summary_bytes"] for value in attribution], "phases": []}
    result["attribution"]["persisted_counts"] = [value["persisted_count"] for value in attribution]
    result["attribution"]["persisted_summary_bytes"] = [value["persisted_summary_bytes"] for value in attribution]
    for metric in ("server_ms", "client_observed_minus_server_ms", "server_remainder_ms"):
        categories = set.intersection(*(set(value[metric]) for value in attribution))
        result["attribution"][metric] = {category: median_populations([value[metric][category] for value in attribution])
                                          for category in sorted(categories)}
    groups = [{(row["source"], row["route_template"], row["phase"], row["operation"]): row for row in value["phases"]}
              for value in attribution]
    for key in sorted(set.intersection(*(set(group) for group in groups))):
        rows = [group[key] for group in groups]
        result["attribution"]["phases"].append({"source": key[0], "route_template": key[1], "phase": key[2],
            "operation": key[3], "duration_ms": median_populations([row["duration_ms"] for row in rows]),
            "outcomes_per_trial": [row["outcomes"] for row in rows]})
    return result


def anchors():
    return [ObservedScenario("admission", concurrency=50, operations=200), ObservedScenario("read", concurrency=50, operations=200),
            ObservedScenario("research", concurrency=10, operations=20), ObservedScenario("research", concurrency=10, operations=20, latency_ms=250),
            ObservedScenario("mixed", concurrency=25, operations=25, latency_ms=250),
            ObservedScenario("sse", concurrency=25, operations=25, latency_ms=250)]


def binding():
    value = scale.git_binding()
    files = ("scripts/benchmarks/obs_001.py", "src/workspace/attribution.py")
    value["obs_harness_sha256"] = hashlib.sha256(b"".join(Path(name).read_bytes() for name in files)).hexdigest()
    value["obs_harness_committed"] = subprocess.run(["git", "ls-files", "--error-unmatch", *files], capture_output=True).returncode == 0
    return value


async def campaign(output: Path, *, smoke=False, max_seconds=1800):
    report = {"protocol": PROTOCOL, "scale_protocol": "scale-002-benchmark-v1", **binding(),
              "environment": environment(), "status": "incomplete", "scenarios": [], "overhead": []}
    if not smoke and (not report["tracked_clean"] or not report["obs_harness_committed"]):
        raise ValueError("canonical campaign requires committed clean harness")
    output.parent.mkdir(parents=True, exist_ok=True)
    began = time.perf_counter()
    configurations = [("anchor", scenario, enabled) for scenario in anchors() for enabled in (False, True)]
    configurations += [("poll", ObservedScenario("worker", concurrency=1, operations=20, poll_ms=poll), True)
                       for poll in (100, 250, 500, 1000)]
    if smoke:
        configurations = [("smoke", ObservedScenario(profile, concurrency=2, operations=2, warmup=1, trials=1, latency_ms=5), True)
                          for profile in ("admission", "read", "research", "mixed", "sse")]
    def checkpoint():
        validate_report(report)
        output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    checkpoint()
    for kind, scenario, enabled in configurations:
        row = {"kind": kind, "binding": scenario.binding(), "enabled": enabled, "trials": []}
        report["scenarios"].append(row)
        for index in range(1, scenario.trials + 1):
            remaining = max_seconds - (time.perf_counter() - began)
            if remaining <= 0: raise runtime_module.BenchmarkFailure("campaign_deadline")
            with tempfile.TemporaryDirectory(prefix="obs001-") as temporary:
                try:
                    result = await asyncio.wait_for(trial(scenario, Path(temporary), index, enabled=enabled), min(remaining, scenario.timeout_seconds + 90))
                except Exception as error:
                    row["failure_category"] = "timeout" if isinstance(error, TimeoutError) else "correctness_or_runtime"
                    checkpoint()
                    raise
            row["trials"].append(result)
            checkpoint()
            print(f"{kind} {scenario.profile} clients={scenario.concurrency} delay={scenario.latency_ms} poll={scenario.poll_ms} enabled={enabled} trial={index} PASS", flush=True)
        row["summary"] = summarize(row["trials"])
        checkpoint()
    for off, on in zip(report["scenarios"][:12:2], report["scenarios"][1:12:2]) if not smoke else ():
        before, after = off["summary"], on["summary"]
        differences = {}
        for metric in ("requests_per_second", "jobs_per_second", "cpu_seconds", "peak_rss_bytes"):
            a, b = before[metric], after[metric]
            differences[metric] = {"disabled": a, "enabled": b, "delta_percent": (b / a - 1) * 100 if a and b is not None else None}
        for quantile in ("p50", "p95"):
            a, b = before["request_ms"][quantile], after["request_ms"][quantile]
            differences["request_" + quantile + "_ms"] = {"disabled": a, "enabled": b, "delta_percent": (b / a - 1) * 100 if a and b is not None else None}
        differences["loop_lag_ms"] = {"disabled": before["loop_lag_ms"], "enabled": after["loop_lag_ms"]}
        report["overhead"].append({"binding": off["binding"], "comparison": differences})
    report["status"] = "complete"
    checkpoint()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=1800, choices=range(60, 3601))
    options = parser.parse_args()
    try:
        asyncio.run(campaign(options.output, smoke=options.smoke, max_seconds=options.max_seconds))
    except Exception:
        print("OBS-001 campaign incomplete; inspect the bounded checkpoint.", flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
