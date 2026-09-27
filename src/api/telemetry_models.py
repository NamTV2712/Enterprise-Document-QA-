"""Strict DATA-005 response models for private analytics and sanitized logs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RatePopulation(_StrictModel):
    value: float | None = Field(ge=0, le=1)
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)


class DurationPopulation(_StrictModel):
    known_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    p50: float | None = Field(default=None, ge=0)
    p95: float | None = Field(default=None, ge=0)


class RequestSummary(_StrictModel):
    terminal_count: int = Field(ge=0)
    outcomes: dict[Literal["succeeded", "rejected", "failed", "cancelled", "interrupted"], int]
    success_rate: RatePopulation
    failure_rate: RatePopulation
    duration_ms: DurationPopulation


class TerminalJobSummary(_StrictModel):
    terminal_count: int = Field(ge=0)
    by_namespace: dict[Literal["pipeline", "evaluation", "model_test"], int]
    by_outcome: dict[Literal["succeeded", "failed", "cancelled", "interrupted"], int]


class AnalyticsSummaryResponse(_StrictModel):
    range: Literal["24h", "7d", "30d"]
    started_at: str
    ended_at: str
    requests: RequestSummary
    terminal_jobs: TerminalJobSummary


class AnalyticsPoint(_StrictModel):
    started_at: str
    ended_at: str
    value: float | int | None = Field(default=None, ge=0)
    denominator: int = Field(ge=0)


class AnalyticsTimeseriesResponse(_StrictModel):
    range: Literal["24h", "7d", "30d"]
    interval: Literal["hour", "day"]
    metric: Literal[
        "request_count",
        "request_failure_count",
        "request_duration_p50_ms",
        "request_duration_p95_ms",
        "terminal_job_count",
    ]
    unit: Literal["count", "milliseconds"]
    started_at: str
    ended_at: str
    points: list[AnalyticsPoint]


class OperationalLogRecordResponse(_StrictModel):
    record_id: str
    occurred_at: str
    category: Literal["request", "job"]
    level: Literal["info", "warning", "error"]
    kind: Literal["request_terminal", "job_terminal"]
    subsystem: Literal["query", "search", "retrieval", "pipeline", "evaluation", "model_test"]
    outcome: Literal["succeeded", "rejected", "failed", "cancelled", "interrupted"]
    correlation_id: str
    domain_id: str | None = None
    route_template: str | None = None
    error_code: str | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    metadata: dict[str, object]


class OperationalLogPageResponse(_StrictModel):
    items: list[OperationalLogRecordResponse]
    next_cursor: str | None
    has_more: bool
    limit: int = Field(ge=1, le=100)
