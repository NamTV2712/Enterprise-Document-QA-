"""Thin, protected EVAL-003 routes over the frozen native job coordinator."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable, Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from src.api.access import AccessGrant, require_execution_access, require_local_workspace_access
from src.api.evaluation_job_models import EvaluationCasePage, EvaluationJobCreateRequest, EvaluationJobPage, EvaluationJobResponse
from src.evaluation.frozen_job_plan import FrozenPlanError
from src.evaluation.job_service import EvaluationJobService, EvaluationRequestError
from src.evaluation.job_store import EvaluationStoreError
from src.workspace.database import WorkspaceDatabaseError
from src.workspace.jobs import JobConflictError, JobDataError, JobLimitError, JobNotFoundError, JobState, JobTransitionError


_REVISION = re.compile(r'^(?:([1-9][0-9]*)|"([1-9][0-9]*)")$')
_SEQUENCE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
MAX_SEQUENCE = 9_223_372_036_854_775_807


def _error(error: Exception) -> HTTPException:
    if isinstance(error, JobNotFoundError):
        return HTTPException(404, "Evaluation job was not found")
    if isinstance(error, (JobConflictError, JobTransitionError)):
        return HTTPException(409, "Evaluation job revision or state conflict")
    if isinstance(error, (EvaluationStoreError, JobDataError, WorkspaceDatabaseError, sqlite3.Error, OSError)):
        return HTTPException(503, "Evaluation workspace is unavailable")
    if isinstance(error, (FrozenPlanError, EvaluationRequestError, JobLimitError, ValueError)):
        return HTTPException(422, str(error))
    return HTTPException(500, "Evaluation request failed")


async def _invoke(operation):
    try:
        return await run_in_threadpool(operation)
    except (JobNotFoundError, JobConflictError, JobTransitionError, JobLimitError,
            EvaluationRequestError, FrozenPlanError, EvaluationStoreError, JobDataError,
            WorkspaceDatabaseError, sqlite3.Error, OSError, ValueError) as error:
        raise _error(error) from error


def _revision(value: str | None) -> int:
    if value is None:
        raise HTTPException(428, "If-Match is required for evaluation cancellation")
    match = _REVISION.fullmatch(value)
    if match is None or len(value) > 21:
        raise HTTPException(422, "If-Match must contain one positive job revision")
    result = int(match.group(1) or match.group(2))
    if result > MAX_SEQUENCE:
        raise HTTPException(422, "If-Match revision is out of bounds")
    return result


def _sequence(value: str | None) -> int:
    if value is None:
        return 0
    if _SEQUENCE.fullmatch(value) is None or len(value) > 19:
        raise HTTPException(422, "Last-Event-ID must be a non-negative sequence")
    result = int(value)
    if result > MAX_SEQUENCE:
        raise HTTPException(422, "Last-Event-ID is out of bounds")
    return result


def _frames(events: tuple[dict, ...]) -> Iterator[str]:
    for event in events:
        data = json.dumps(event, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        yield f"id: {event['sequence']}\nevent: {event['event_type']}\ndata: {data}\n\n"


def create_evaluation_job_router(get_service: Callable[[], EvaluationJobService]) -> APIRouter:
    router = APIRouter()

    @router.get("/evaluation/jobs", response_model=EvaluationJobPage)
    async def evaluation_jobs(
        state: JobState | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> EvaluationJobPage:
        return EvaluationJobPage.model_validate(await _invoke(lambda: get_service().list(state=state, page=page, page_size=page_size)))

    @router.post("/evaluation/jobs", response_model=EvaluationJobResponse, status_code=201)
    async def create_evaluation_job(
        body: EvaluationJobCreateRequest, background: BackgroundTasks, response: Response,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> EvaluationJobResponse:
        if idempotency_key is None or _IDEMPOTENCY.fullmatch(idempotency_key) is None:
            raise HTTPException(422, "A bounded Idempotency-Key header is required")
        service = get_service()
        job = await _invoke(lambda: service.create(
            artifact_id=body.artifact_id, engine=body.engine, metrics=body.metrics,
            mode=body.mode, budget=body.budget, idempotency_key=idempotency_key,
        ))
        if job.state == "queued":
            background.add_task(service.run, job.job_id)
        result = await _invoke(lambda: service.get(job.job_id))
        response.headers["ETag"] = f'"{result["revision"]}"'
        return EvaluationJobResponse.model_validate(result)

    @router.get("/evaluation/jobs/{job_id}", response_model=EvaluationJobResponse)
    async def evaluation_job(
        job_id: str, response: Response,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> EvaluationJobResponse:
        result = await _invoke(lambda: get_service().get(job_id))
        response.headers["ETag"] = f'"{result["revision"]}"'
        return EvaluationJobResponse.model_validate(result)

    @router.get("/evaluation/jobs/{job_id}/results", response_model=EvaluationCasePage)
    async def evaluation_job_results(
        job_id: str, page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> EvaluationCasePage:
        return EvaluationCasePage.model_validate(await _invoke(
            lambda: get_service().results(job_id, page=page, page_size=page_size)
        ))

    @router.post("/evaluation/jobs/{job_id}/cancel", response_model=EvaluationJobResponse)
    async def cancel_evaluation_job(
        job_id: str, response: Response,
        if_match: str | None = Header(default=None, alias="If-Match"),
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> EvaluationJobResponse:
        result = await _invoke(lambda: get_service().cancel(job_id, expected_revision=_revision(if_match)))
        response.headers["ETag"] = f'"{result["revision"]}"'
        return EvaluationJobResponse.model_validate(result)

    @router.get("/evaluation/jobs/{job_id}/events")
    async def evaluation_job_events(
        job_id: str, last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> StreamingResponse:
        events = await _invoke(lambda: get_service().events(job_id, after_sequence=_sequence(last_event_id)))
        return StreamingResponse(
            _frames(events), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
