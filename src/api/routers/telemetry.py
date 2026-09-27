"""Protected DATA-005 analytics and sanitized operational-log reads."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.api.access import AccessGrant, require_local_workspace_access
from src.api.telemetry_models import (
    AnalyticsSummaryResponse,
    AnalyticsTimeseriesResponse,
    OperationalLogPageResponse,
)
from src.workspace.database import WorkspaceDatabaseError
from src.workspace.telemetry import (
    TelemetryConflictError,
    TelemetryDataError,
    TelemetryService,
    TelemetryValidationError,
)


T = TypeVar("T")


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, TelemetryValidationError):
        return HTTPException(status_code=422, detail=str(error))
    if isinstance(
        error,
        (TelemetryConflictError, TelemetryDataError, WorkspaceDatabaseError, sqlite3.Error, OSError),
    ):
        return HTTPException(status_code=503, detail="Operational telemetry is unavailable")
    return HTTPException(status_code=500, detail="Operational telemetry request failed")


async def _invoke(operation: Callable[[], T]) -> T:
    try:
        return await run_in_threadpool(operation)
    except (
        TelemetryValidationError,
        TelemetryConflictError,
        TelemetryDataError,
        WorkspaceDatabaseError,
        sqlite3.Error,
        OSError,
    ) as error:
        raise _http_error(error) from error


def create_telemetry_router(get_service: Callable[[], TelemetryService]) -> APIRouter:
    """Build thin private reads over the application-owned workspace service."""
    router = APIRouter()

    @router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
    async def analytics_summary(
        range: Literal["24h", "7d", "30d"] = Query(default="24h"),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> AnalyticsSummaryResponse:
        result = await _invoke(lambda: get_service().summary(range))
        return AnalyticsSummaryResponse.model_validate(result)

    @router.get("/analytics/timeseries", response_model=AnalyticsTimeseriesResponse)
    async def analytics_timeseries(
        range: Literal["24h", "7d", "30d"] = Query(default="24h"),
        interval: Literal["hour", "day"] = Query(default="hour"),
        metric: Literal[
            "request_count",
            "request_failure_count",
            "request_duration_p50_ms",
            "request_duration_p95_ms",
            "terminal_job_count",
        ] = Query(default="request_count"),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> AnalyticsTimeseriesResponse:
        result = await _invoke(lambda: get_service().timeseries(range, interval, metric))
        return AnalyticsTimeseriesResponse.model_validate(result)

    @router.get("/logs", response_model=OperationalLogPageResponse)
    async def operational_logs(
        category: Literal["request", "job"] | None = Query(default=None),
        level: Literal["info", "warning", "error"] | None = Query(default=None),
        cursor: str | None = Query(default=None, max_length=512),
        limit: int = Query(default=50, ge=1, le=100),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> OperationalLogPageResponse:
        result = await _invoke(
            lambda: get_service().logs(
                category=category,
                level=level,
                cursor=cursor,
                limit=limit,
            )
        )
        return OperationalLogPageResponse.model_validate(
            {
                "items": [item.__dict__ for item in result.items],
                "next_cursor": result.next_cursor,
                "has_more": result.has_more,
                "limit": result.limit,
            }
        )

    return router
