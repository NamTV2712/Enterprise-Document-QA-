"""Small in-process, privacy-safe request telemetry for the single-worker API."""

from __future__ import annotations

import time
from collections import Counter
from threading import Lock
from typing import Any


class RequestTelemetry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: Counter[str] = Counter()
        self._errors: Counter[str] = Counter()
        self._latency_seconds: Counter[str] = Counter()
        self._latencies: dict[str, list[float]] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._streaming_requests: int = 0
        self._decomposed_requests: int = 0
        self._started_at = time.time()

    def record(self, route: str, status_code: int, elapsed_seconds: float) -> None:
        with self._lock:
            self._requests[route] += 1
            self._latency_seconds[route] += elapsed_seconds
            if status_code >= 400:
                self._errors[f"{route}:{status_code}"] += 1
            # Track individual latencies for percentile calculation
            if route not in self._latencies:
                self._latencies[route] = []
            self._latencies[route].append(elapsed_seconds)
            # Keep only last 1000 latencies per route to bound memory
            if len(self._latencies[route]) > 1000:
                self._latencies[route] = self._latencies[route][-1000:]

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_streaming_request(self) -> None:
        with self._lock:
            self._streaming_requests += 1

    def record_decomposed_request(self) -> None:
        with self._lock:
            self._decomposed_requests += 1

    def _percentile(self, data: list[float], p: float) -> float:
        """Calculate p-th percentile from a sorted list."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[-1] * 1000
        return (sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])) * 1000

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_latencies = {}
            p50_latencies = {}
            p95_latencies = {}
            p99_latencies = {}
            for route, count in sorted(self._requests.items()):
                avg_latencies[route] = round(
                    1000 * self._latency_seconds[route] / count, 2
                )
                latencies = self._latencies.get(route, [])
                p50_latencies[route] = round(self._percentile(latencies, 0.5), 2)
                p95_latencies[route] = round(self._percentile(latencies, 0.95), 2)
                p99_latencies[route] = round(self._percentile(latencies, 0.99), 2)

            total_requests = sum(self._requests.values())
            total_errors = sum(self._errors.values())
            uptime_seconds = time.time() - self._started_at
            total_cache = self._cache_hits + self._cache_misses

            return {
                "uptime_seconds": round(uptime_seconds, 1),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": round(total_errors / max(total_requests, 1) * 100, 2),
                "requests_by_route": dict(sorted(self._requests.items())),
                "errors_by_route_status": dict(sorted(self._errors.items())),
                "latency_ms": {
                    "average": avg_latencies,
                    "p50": p50_latencies,
                    "p95": p95_latencies,
                    "p99": p99_latencies,
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": round(self._cache_hits / max(total_cache, 1) * 100, 2),
                },
                "request_types": {
                    "streaming": self._streaming_requests,
                    "decomposed": self._decomposed_requests,
                },
            }
