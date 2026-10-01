"""Request-scoped, additive execution timing for user-visible RAG traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any
from uuid import uuid4


@dataclass
class ExecutionTrace:
    """Capture elapsed wall time for work that actually occurred in one request."""

    started_at: float = field(default_factory=perf_counter)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    stages: list[dict[str, object]] = field(default_factory=list)
    sequence: int = 0

    def stage_event(
        self,
        stage_id: str,
        status: str,
        *,
        started_at: float | None = None,
        parent_stage_id: str | None = None,
        counters: dict[str, int] | None = None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> dict[str, Any]:
        """Return one additive SSE stage event with measured request ordering."""
        self.sequence += 1
        event: dict[str, Any] = {
            "version": 1,
            "request_id": self.request_id,
            "sequence": self.sequence,
            "stage_id": stage_id,
            "status": status,
        }
        if parent_stage_id is not None:
            event["parent_stage_id"] = parent_stage_id
        if started_at is not None:
            event["elapsed_ms"] = round((perf_counter() - started_at) * 1000, 2)
        if counters:
            event["counters"] = counters
        if metadata:
            event["metadata"] = metadata
        return event

    def mark(self, name: str, started_at: float, *, status: str = "completed") -> None:
        self.stages.append(
            {
                "name": name,
                "elapsed_ms": round((perf_counter() - started_at) * 1000, 2),
                "status": status,
            }
        )

    def payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "elapsed_ms": round((perf_counter() - self.started_at) * 1000, 2),
            "stages": list(self.stages),
        }
