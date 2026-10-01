"""Bounded CAPACITY-001 characterization over the existing SCALE/OBS/WORKER harness."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from unittest.mock import patch

import httpx

from scripts.benchmarks import obs_001 as obs, worker_002 as worker
from scripts.benchmarks import scale_002_runtime as runtime
from scripts.benchmarks.scale_002_stats import environment, validate_report
from src.workspace.attribution import statistics

PROTOCOL = "capacity-001-v1"
MAX_JOBS = 256
TOOLS = ("search_documents", "inspect_retrieval", "read_document", "ask_rag")


def union_length(intervals):
    """Length of an interval union in monotonic nanoseconds, including overlaps."""
    end = None
    total = 0
    for start, stop in sorted(intervals):
        if stop < start:
            raise runtime.BenchmarkFailure("invalid_capacity_interval")
        total += max(0, stop - max(start, end if end is not None else start))
        end = max(stop, end if end is not None else stop)
    return total


def occupancy(trace):
    """Exclusive partition by union subtraction; inclusive phases remain separate."""
    roots = [r for r in trace.records if r.phase == "worker.service"]
    if trace.dropped or len(roots) != 1:
        raise runtime.BenchmarkFailure("incomplete_capacity_trace")
    root = roots[0]

    def intervals(phases):
        return [(max(root.start_ns, r.start_ns), min(root.end_ns, r.end_ns))
                for r in trace.records if r.phase in phases
                and r.end_ns > root.start_ns and r.start_ns < root.end_ns]

    groups = {
        "provider": intervals({"agent.provider", "generator.transport"}),
        "tools": intervals({"agent.tool." + name for name in TOOLS}),
        "persistence": intervals({"agent.persist_result"}),
        "workspace": intervals({"workspace.read", "workspace.critical_section",
                                 "workspace.serialized_wait", "workspace.connection_open",
                                 "workspace.transaction", "workspace.initialize"}),
    }
    result = {"service": root.duration_ms}
    used = []
    for name, spans in groups.items():
        result[name] = (union_length(used + spans) - union_length(used)) / 1_000_000
        used.extend(spans)
    result["unattributed"] = root.duration_ms - union_length(used) / 1_000_000
    if result["unattributed"] < -1e-6:
        raise runtime.BenchmarkFailure("capacity_partition_outside_service")
    result["unattributed"] = max(0, result["unattributed"])
    for phase in ("agent.decision", "agent.provider", "agent.persist_result") + tuple(
            "agent.tool." + name for name in TOOLS):
        result[phase] = union_length(intervals({phase})) / 1_000_000
    return result


@dataclass(frozen=True)
class Point:
    name: str
    kind: str = "worker"
    workers: int = 2
    delay_ms: int = 0
    clients: int = 25
    operations: int = 25
    trials: int = 3
    tool: str | None = None
    provider_limit: int | None = None

    def worker_point(self):
        return worker.Point(self.name, self.kind, self.workers, self.clients,
                            self.operations, self.delay_ms, trials=self.trials)


def points():
    return [Point(f"workers-{n}-delay-{d}", workers=n, delay_ms=d)
            for d in (0, 250, 100, 500) for n in (1, 2, 4, 8)] + [
        Point(f"research-10-{d}", "research", delay_ms=d, clients=10, operations=20)
        for d in (0, 250, 500)] + [
        Point(f"mixed-25-{n}-250", "mixed", workers=n, delay_ms=250)
        for n in (2, 4, 8)] + [
        Point("tool-" + name, tool=name) for name in ("inspect_retrieval", "ask_rag")] + [
        Point("idle", "idle", clients=1, operations=20, trials=1),
        Point("restart", "restart", clients=20, operations=20, trials=1),
    ] + [
        Point(f"gate-2-{kind}-{n}-250", kind, workers=n, delay_ms=250, provider_limit=2)
        for kind in ("worker", "mixed") for n in (4, 8)
    ]


@contextmanager
def tool_variant(name):
    """Only scripted synthetic decisions/grants differ; actual tool adapters run."""
    if name is None:
        yield
        return
    if name not in ("inspect_retrieval", "ask_rag"):
        raise ValueError("unsupported tool variant")
    original_create = runtime.Runtime.create
    original_transport = httpx.MockTransport.handle_async_request
    with patch.dict(os.environ):
        from tests.integration.harness_server import FakeRetriever
    original_inspect = FakeRetriever.inspect

    def inspect(retriever, *args, **kwargs):
        # The old browser fixture predates the typed Agent observation. Preserve
        # its synthetic scores/selection and label that boundary explicitly.
        trace = original_inspect(retriever, *args, **kwargs)
        trace["trace_version"] = "capacity-synthetic-retrieval-v1"
        trace["score_semantics"] = {"bm25_score": "synthetic token overlap",
            "dense_score": "synthetic reciprocal rank", "rrf_score": "synthetic reciprocal rank",
            "cross_encoder_score": "not executed"}
        for stage in trace["stages"]:
            stage["status"] = "skipped" if stage.get("skipped") else "executed"
        return trace

    async def create(bench, ordinal, research=False):
        if research:
            raise runtime.BenchmarkFailure("tool_variant_research_not_supported")
        response = await bench.request("POST", "/agent/runs", expected=201,
            json={"goal": "Research benchmark filing evidence.",
                  "allow_decision_provider_execution": True,
                  "allowed_tools": list(TOOLS), "allow_provider_tool_execution": name == "ask_rag"},
            headers={"Idempotency-Key": f"bench-{ordinal}"})
        data = response.json()
        if data["state"] != "queued":
            raise runtime.BenchmarkFailure("creation_not_queued")
        return data["run_id"]

    async def transport(mock, request):
        response = await original_transport(mock, request)
        body = response.json()
        wire = json.loads(body["choices"][0]["message"]["content"])
        if wire["decision"]["kind"] == "tool":
            wire["decision"]["tool_name"] = name
            wire["decision"]["arguments"] = [
                {"name": "question", "value": "Apple filing revenue evidence"},
                {"name": "ticker", "value": "AAPL"}]
            body["choices"][0]["message"]["content"] = json.dumps(wire)
            return httpx.Response(response.status_code, json=body, request=request)
        return response

    with patch.object(runtime.Runtime, "create", create), \
            patch.object(FakeRetriever, "inspect", inspect), \
            patch.object(httpx.MockTransport, "handle_async_request", transport):
        yield


@contextmanager
def provider_control(limit):
    """Diagnostic only: fixed workers wait before the existing decision adapter."""
    if limit is None:
        yield
        return
    from src.agent.provider import GroqDecisionModel
    semaphore = asyncio.BoundedSemaphore(limit)
    original = GroqDecisionModel.decide

    async def decide(model, request):
        async with semaphore:
            return await original(model, request)

    with patch.object(GroqDecisionModel, "decide", decide):
        yield


async def trial(point, directory, index):
    from src.api.telemetry import RequestTelemetry
    from src.api import app as application
    original = RequestTelemetry.record_attribution
    original_reset = runtime.Observer.reset
    original_publish = application._publish_performance
    captured = {}
    telemetry_ms = {}

    def reset(observer):
        original_reset(observer)
        captured.clear()
        telemetry_ms.clear()

    async def publish(trace, *, correlation_id, route_template):
        started = time.perf_counter()
        await original_publish(trace, correlation_id=correlation_id, route_template=route_template)
        if trace.source == "worker" and correlation_id in captured:
            telemetry_ms[correlation_id] = (time.perf_counter() - started) * 1000

    def completed(owner, trace, *, correlation_id, route_template, persisted=False):
        original(owner, trace, correlation_id=correlation_id,
                 route_template=route_template, persisted=persisted)
        if trace.source == "worker":
            if len(captured) >= MAX_JOBS or correlation_id in captured:
                raise runtime.BenchmarkFailure("capacity_capture_budget_or_identity")
            captured[correlation_id] = occupancy(trace)

    # OBS invokes the class completion seam and excludes warmup IDs itself.
    with patch.object(RequestTelemetry, "record_attribution", completed), \
            patch.object(runtime.Observer, "reset", reset), \
            patch.object(application, "_publish_performance", publish), \
            tool_variant(point.tool), provider_control(point.provider_limit):
        result = await worker.measured_trial(point.worker_point(), directory, index)
    measured_count = result["correctness"]["terminal_statuses"].get("succeeded", 0)
    values = list(captured.values())
    if len(values) != measured_count or len(telemetry_ms) != measured_count:
        raise runtime.BenchmarkFailure("missing_capacity_workers")
    if point.provider_limit is not None and result["scheduler"]["peak_provider_calls"] > point.provider_limit:
        raise runtime.BenchmarkFailure("diagnostic_provider_bound")
    result["occupancy"] = {"population": "per_completed_worker_service",
        "exclusive_priority": ["provider", "tools", "persistence", "workspace", "unattributed"],
        "phases_ms": {key: statistics([v[key] for v in values]) for key in values[0]} if values else {}}
    result["post_service_telemetry_ms"] = statistics(list(telemetry_ms.values()))
    validate_report(result)
    return result


def summarize(trials):
    result = obs.summarize(trials)
    result["scheduler"] = worker.scheduler_summary(trials)
    phases = [t["occupancy"]["phases_ms"] for t in trials]
    result["occupancy_ms"] = {key: obs.median_populations([p[key] for p in phases])
                              for key in phases[0]}
    result["post_service_telemetry_ms"] = obs.median_populations([t["post_service_telemetry_ms"] for t in trials])
    return result


async def campaign(output, *, smoke=False, selected=None, max_seconds=1800):
    binding = obs.binding()
    report = {"protocol": PROTOCOL, **binding, "environment": environment(),
        "driver_committed": subprocess.run(["git", "ls-files", "--error-unmatch",
            "scripts/benchmarks/capacity_001.py"], capture_output=True).returncode == 0,
        "driver_sha256": hashlib.sha256(b"".join((Path(__file__).parent / name).read_bytes()
            for name in ("capacity_001.py", "worker_002.py", "worker_002_runtime.py"))).hexdigest(),
        "status": "incomplete", "scenarios": []}
    if not smoke and (not binding["tracked_clean"] or not report["driver_committed"]):
        raise ValueError("canonical runtime must be tracked clean")
    matrix = points()
    if selected:
        if set(selected) - {p.name for p in matrix}:
            raise ValueError("unknown capacity point")
        matrix = [p for p in matrix if p.name in selected]
    if smoke:
        matrix = [Point(p.name, p.kind, workers=2, delay_ms=5, clients=2,
                        operations=2, trials=1, tool=p.tool, provider_limit=p.provider_limit) for p in matrix]
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        validate_report(report)
        output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")

    started = time.perf_counter()
    save()
    for point in matrix:
        row = {"binding": asdict(point), "trials": []}
        report["scenarios"].append(row)
        for index in range(1, point.trials + 1):
            remaining = max_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                raise TimeoutError("capacity campaign deadline")
            with tempfile.TemporaryDirectory(prefix="capacity001-") as directory:
                try:
                    value = await asyncio.wait_for(trial(point, Path(directory), index), min(remaining, 330))
                except Exception:
                    row["failure_category"] = "correctness_or_runtime"
                    save()
                    raise
            row["trials"].append(value)
            save()
            print(f"{point.name} trial={index} PASS", flush=True)
        row["summary"] = summarize(row["trials"])
        save()
    report["status"] = "complete"
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--points", nargs="+")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(campaign(args.output, smoke=args.smoke, selected=args.points))
    except Exception:
        print("CAPACITY-001 incomplete; inspect bounded checkpoint.", flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
