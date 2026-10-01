"""Versioned SCALE-002 configuration, explicit statistics and safe JSON reports."""

from __future__ import annotations

import importlib.metadata
import math
import os
import platform
import sqlite3
import statistics
from dataclasses import asdict, dataclass
from typing import Iterable


PROTOCOL = "scale-002-benchmark-v1"
PROFILES = ("admission", "read", "worker", "research", "sse", "mixed", "cancel", "degraded")
PERCENTILE_MINIMUMS = {50: 2, 95: 20, 99: 100}


def working_set_bytes() -> int | None:
    """Optional Windows working-set sample; no process identity or new package."""
    if os.name != "nt": return None
    import ctypes
    class Counters(ctypes.Structure):
        _fields_ = [("size", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ("peak", "working", "paged_peak", "paged",
                                                "nonpaged_peak", "nonpaged", "pagefile", "pagefile_peak", "private")]
    counters = Counters()
    counters.size = ctypes.sizeof(counters)
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(counters), counters.size):
        return counters.working
    return None


def finite_samples(values: Iterable[float]) -> list[float]:
    result = list(values)
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) or v < 0 for v in result):
        raise ValueError("benchmark samples must be finite non-negative numbers")
    return sorted(result)


def percentiles(values: Iterable[float]) -> dict:
    """Nearest rank ceil(p*n), with an explicit minimum per percentile."""
    ordered = finite_samples(values)
    result = {"samples": len(ordered), "max": max(ordered) if ordered else None}
    for percentile, minimum in PERCENTILE_MINIMUMS.items():
        enough = len(ordered) >= minimum
        result[f"p{percentile}"] = (ordered[math.ceil(percentile * len(ordered) / 100) - 1]
                                      if enough else None)
        result[f"p{percentile}_status"] = "available" if enough else "insufficient_samples"
    return result


def throughput(completed: int, seconds: float) -> float | None:
    if type(completed) is not int or completed < 0:
        raise ValueError("operation count is invalid")
    finite_samples([seconds])
    return completed / seconds if seconds > 0 else None


def lifecycle_durations(created: float, claimed: float, terminal: float) -> tuple[float, float, float]:
    finite_samples([created, claimed, terminal])
    if not created <= claimed <= terminal:
        raise ValueError("lifecycle commit times are not monotonic")
    return ((claimed - created) * 1000, (terminal - claimed) * 1000,
            (terminal - created) * 1000)


def summarize_trials(trials: list[dict]) -> dict:
    """Median of per-trial measurements, never merge heterogeneous samples."""
    if not trials or any(trial["status"] != "complete" for trial in trials):
        raise ValueError("cannot summarize an incomplete trial")
    keys = ("requests_per_second", "jobs_per_second", "drain_ms", "cpu_seconds", "peak_rss_bytes")
    result = {"trials": len(trials), "aggregation": "median_of_trial_statistics"}
    for key in keys:
        values = [trial.get(key) for trial in trials if trial.get(key) is not None]
        result[key] = statistics.median(values) if len(values) == len(trials) else None
    for metric in ("request_ms", "queue_wait_ms", "service_ms", "end_to_end_ms", "claim_ms",
                   "write_transaction_ms", "write_lock_wait_ms", "provider_ms", "tool_ms",
                   "event_delivery_ms", "loop_lag_ms"):
        result[metric] = {}
        for percentile in ("p50", "p95", "p99", "max"):
            values = [trial[metric][percentile] for trial in trials
                      if trial[metric][percentile] is not None]
            result[metric][percentile] = (statistics.median(values) if len(values) == len(trials) else None)
        result[metric]["samples_per_trial"] = [trial[metric]["samples"] for trial in trials]
    return result


@dataclass(frozen=True)
class Scenario:
    profile: str
    concurrency: int = 1
    workers: int = 2
    operations: int = 20
    latency_ms: int = 0
    trials: int = 3
    warmup: int = 4
    poll_ms: int = 500
    mode: str = "hermetic"

    def __post_init__(self):
        if self.profile not in PROFILES or self.mode not in ("hermetic", "artifact"):
            raise ValueError("unknown benchmark profile or mode")
        for name, low, high in (("concurrency", 1, 100), ("workers", 1, 8),
                                ("operations", 1, 1000), ("latency_ms", 0, 1000),
                                ("trials", 1, 5), ("warmup", 1, 20), ("poll_ms", 100, 5000)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError("benchmark configuration is out of bounds")
        if self.profile == "cancel" and (self.operations != 6 or self.workers != 2):
            raise ValueError("cancellation workload requires six jobs and two workers")

    @property
    def timeout_seconds(self) -> float:
        decisions = 3 if self.profile in ("research", "sse", "mixed") else 2
        return min(240.0, max(30.0, 30 + 3 * self.operations * decisions * self.latency_ms / 1000 / self.workers))

    def binding(self) -> dict:
        return {**asdict(self), "timeout_seconds": self.timeout_seconds,
                "synthetic_provider_latency_ms": self.latency_ms,
                "shutdown_grace_ms": 5000, "sqlite_busy_timeout_ms": 5000,
                "database": "isolated_SQLite_WAL_synchronous_NORMAL",
                "http": "loopback_TCP_same_process_client_and_server",
                "fixture": "synthetic-sec-v1" if self.mode == "hermetic" else "local_artifacts",
                "warmup_policy": "per_trial_same_runtime_excluded_from_all_samples",
                "percentile_algorithm": "nearest_rank_ceil_p_times_n",
                "percentile_minimum_samples": {str(k): v for k, v in PERCENTILE_MINIMUMS.items()},
                "time_source": "time.perf_counter_commit_boundary_and_client",
                "cpu_scope": "combined_client_server_process"}


def environment() -> dict:
    result = {"os_family": platform.system(), "os_version": platform.version(),
              "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
              "logical_cpus": os.cpu_count(), "ram_bytes": None,
              "process_rss": "unavailable", "cpu": "stdlib_process_time",
              "runtime_versions": {name: importlib.metadata.version(name)
                                   for name in ("fastapi", "starlette", "httpx", "uvicorn", "groq", "pydantic")}}
    if os.name == "nt":
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in ("total", "available", "page_total", "page_available",
                                                      "virtual_total", "virtual_available", "extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result["ram_bytes"] = status.total
        if working_set_bytes() is not None: result["process_rss"] = "Windows_working_set_sampled"
    return result


def validate_report(report: dict) -> None:
    """Enforce finite output and refuse content/credential/path fields recursively."""
    forbidden = {"hostname", "username", "path", "goal", "content", "messages", "authorization",
                 "cookie", "cookies", "api_key", "bearer", "token", "headers", "transcript"}
    def walk(value):
        if isinstance(value, dict):
            if any(str(key).lower() in forbidden for key in value):
                raise ValueError("unsafe benchmark report field")
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("nonfinite benchmark report")
        elif isinstance(value, str) and ("Bearer " in value or ":\\" in value or "/Users/" in value):
            raise ValueError("unsafe benchmark report string")
    walk(report)
