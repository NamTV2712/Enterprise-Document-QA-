"""Provider-free API-007 pipeline definition and protected run staging routes."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from typing import TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from src.api.access import (
    AccessGrant,
    require_execution_access,
    require_local_workspace_access,
    require_public_provider_free_access,
)
from src.api.pipeline import (
    MAX_EVENT_SEQUENCE,
    MAX_PAGE_SIZE,
    PipelineInputNotFoundError,
    PipelineRequestError,
    PipelineService,
    pipeline_definition,
    validate_pipeline_request,
)
from src.api.pipeline_models import (
    PipelineDefinitionResponse,
    PipelineRunCreateRequest,
    PipelineRunEventResponse,
    PipelineRunPageResponse,
    PipelineRunResponse,
)
from src.workspace.database import WorkspaceDatabaseError
from src.workspace.jobs import (
    JobConflictError,
    JobDataError,
    JobLimitError,
    JobNotFoundError,
    JobState,
    JobTransitionError,
)


_REVISION_HEADER = re.compile(r'^(?:([1-9][0-9]*)|"([1-9][0-9]*)")$')
_SEQUENCE_HEADER = re.compile(r"^(?:0|[1-9][0-9]*)$")
T = TypeVar("T")


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, (JobNotFoundError, PipelineInputNotFoundError)):
        return HTTPException(status_code=404, detail="Pipeline resource was not found")
    if isinstance(error, (JobConflictError, JobTransitionError)):
        return HTTPException(status_code=409, detail="Pipeline run revision or state conflict")
    if isinstance(error, (JobLimitError, PipelineRequestError)):
        return HTTPException(status_code=422, detail=str(error))
    if isinstance(error, (JobDataError, WorkspaceDatabaseError, sqlite3.Error, OSError)):
        return HTTPException(status_code=503, detail="Pipeline workspace is unavailable")
    return HTTPException(status_code=500, detail="Pipeline request failed")


def _raise(error: Exception) -> None:
    raise _http_error(error) from error


async def _invoke(operation: Callable[[], T]) -> T:
    """Run synchronous SQLite work off-loop and expose only safe errors."""
    try:
        return await run_in_threadpool(operation)
    except (
        JobNotFoundError,
        PipelineInputNotFoundError,
        JobConflictError,
        JobTransitionError,
        JobLimitError,
        PipelineRequestError,
        JobDataError,
        WorkspaceDatabaseError,
        sqlite3.Error,
        OSError,
    ) as error:
        _raise(error)


def _parse_revision(value: str | None) -> int:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="If-Match is required for pipeline cancellation",
        )
    match = _REVISION_HEADER.fullmatch(value)
    if match is None:
        raise HTTPException(status_code=422, detail="If-Match must contain one positive run revision")
    revision = int(match.group(1) or match.group(2))
    if revision > MAX_EVENT_SEQUENCE:
        raise HTTPException(status_code=422, detail="If-Match revision is out of bounds")
    return revision


def _parse_last_event_id(value: str | None) -> int:
    if value is None:
        return 0
    if _SEQUENCE_HEADER.fullmatch(value) is None:
        raise HTTPException(status_code=422, detail="Last-Event-ID must be a non-negative sequence")
    sequence = int(value)
    if sequence > MAX_EVENT_SEQUENCE:
        raise HTTPException(status_code=422, detail="Last-Event-ID is out of bounds")
    return sequence


def _set_run_etag(response: Response, run: PipelineRunResponse) -> None:
    response.headers["ETag"] = f'"{run.revision}"'


def _sse_frames(events: tuple[PipelineRunEventResponse, ...]) -> Iterator[str]:
    for event in events:
        data = json.dumps(
            event.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {data}\n\n"


def create_pipeline_router(get_service: Callable[[], PipelineService]) -> APIRouter:
    """Build the pipeline API over an application-owned lazy service factory."""
    router = APIRouter()

    @router.get("/pipeline", response_model=PipelineDefinitionResponse)
    async def get_pipeline_definition(
        _grant: AccessGrant = Depends(require_public_provider_free_access),
    ) -> PipelineDefinitionResponse:
        """Return static registered capabilities without touching local storage."""
        return pipeline_definition()

    @router.get("/pipeline/runs", response_model=PipelineRunPageResponse)
    async def list_pipeline_runs(
        _grant: AccessGrant = Depends(require_local_workspace_access),
        state: JobState | None = Query(default=None),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    ) -> PipelineRunPageResponse:
        return await _invoke(
            lambda: get_service().list_runs(
                state=state,
                page=page,
                page_size=page_size,
            )
        )

    @router.post("/pipeline/runs", response_model=PipelineRunResponse, status_code=201)
    async def stage_pipeline_run(
        body: PipelineRunCreateRequest,
        response: Response,
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> PipelineRunResponse:
        try:
            validate_pipeline_request(body)
        except (PipelineInputNotFoundError, PipelineRequestError) as error:
            _raise(error)
        run = await _invoke(lambda: get_service().stage(body))
        _set_run_etag(response, run)
        return run

    @router.get("/pipeline/runs/{run_id}", response_model=PipelineRunResponse)
    async def get_pipeline_run(
        run_id: str,
        response: Response,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> PipelineRunResponse:
        run = await _invoke(lambda: get_service().get_run(run_id))
        _set_run_etag(response, run)
        return run

    @router.post("/pipeline/runs/{run_id}/cancel", response_model=PipelineRunResponse)
    async def cancel_pipeline_run(
        run_id: str,
        response: Response,
        if_match: str | None = Header(default=None, alias="If-Match"),
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> PipelineRunResponse:
        revision = _parse_revision(if_match)
        run = await _invoke(
            lambda: get_service().cancel_run(
                run_id,
                expected_revision=revision,
            )
        )
        _set_run_etag(response, run)
        return run

    @router.get("/pipeline/runs/{run_id}/events")
    async def get_pipeline_run_events(
        run_id: str,
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> StreamingResponse:
        sequence = _parse_last_event_id(last_event_id)
        events = await _invoke(
            lambda: get_service().list_events(
                run_id,
                after_sequence=sequence,
            )
        )
        return StreamingResponse(
            _sse_frames(events),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
