"""Small in-process, privacy-safe request telemetry for the single-worker API."""

from __future__ import annotations

from collections import Counter
from threading import Lock


class RequestTelemetry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests = Counter()
        self._errors = Counter()
        self._latency_seconds = Counter()

    def record(self, route: str, status_code: int, elapsed_seconds: float) -> None:
        with self._lock:
            self._requests[route] += 1
            self._latency_seconds[route] += elapsed_seconds
            if status_code >= 400:
                self._errors[f"{route}:{status_code}"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "requests_by_route": dict(sorted(self._requests.items())),
                "errors_by_route_status": dict(sorted(self._errors.items())),
                "average_latency_ms_by_route": {
                    route: round(1000 * self._latency_seconds[route] / count, 2)
                    for route, count in sorted(self._requests.items())
                },
            }
