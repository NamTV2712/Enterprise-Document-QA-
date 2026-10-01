"""Private, revisioned AGENT-003 routes over DATA-004 and AGENT-002."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable, Iterator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from src.agent.durable import AgentDurableService
from src.agent.durable_models import (
    AgentRunCreateRequest, AgentRunEventResponse, AgentRunPage,
    AgentRunResponse, AgentRunResultResponse,
)
from src.agent.evaluation import evaluate_durable_agent_run
from src.agent.evaluation_models import AgentEvaluationReport, CorruptAgentSnapshot
from src.api.access import AccessGrant, require_execution_access, require_local_workspace_access
from src.workspace.database import WorkspaceDatabaseError
from src.workspace.jobs import (
    JobConflictError, JobDataError, JobLimitError, JobNotFoundError,
    JobState, JobTransitionError,
)


_REVISION = re.compile(r'^(?:([1-9][0-9]*)|"([1-9][0-9]*)")$')
_SEQUENCE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
MAX_SEQUENCE = 9_223_372_036_854_775_807


def _error(error: Exception) -> HTTPException:
    if isinstance(error, JobNotFoundError):
        return HTTPException(404, "Agent run was not found")
    if isinstance(error, (JobConflictError, JobTransitionError)):
        return HTTPException(409, "Agent run revision or state conflict")
    if isinstance(error, (JobDataError, WorkspaceDatabaseError, sqlite3.Error, OSError)):
        return HTTPException(503, "Agent workspace is unavailable")
    if isinstance(error, (JobLimitError, ValueError)):
        return HTTPException(422, str(error))
    return HTTPException(500, "Agent request failed")


async def _invoke(operation):
    try:
        return await run_in_threadpool(operation)
    except (JobNotFoundError, JobConflictError, JobTransitionError, JobLimitError,
            JobDataError, WorkspaceDatabaseError, sqlite3.Error, OSError, ValueError) as error:
        raise _error(error) from error


def _revision(value: str | None) -> int:
    if value is None:
        raise HTTPException(428, "If-Match is required for Agent cancellation")
    match = _REVISION.fullmatch(value)
    if match is None or len(value) > 21:
        raise HTTPException(422, "If-Match must contain one positive run revision")
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


def _frames(events: tuple[AgentRunEventResponse, ...]) -> Iterator[str]:
    for event in events:
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False,
                             allow_nan=False, separators=(",", ":"))
        yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {payload}\n\n"


def create_agent_run_router(get_service: Callable[[], AgentDurableService]) -> APIRouter:
    router = APIRouter()

    @router.get("/agent/runs", response_model=AgentRunPage)
    async def agent_runs(
        state: JobState | None = Query(default=None), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> AgentRunPage:
        return await _invoke(lambda: get_service().list(state=state, page=page, page_size=page_size))

    @router.post("/agent/runs", response_model=AgentRunResponse, status_code=201)
    async def create_agent_run(
        body: AgentRunCreateRequest, response: Response,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> AgentRunResponse:
        if idempotency_key is None or _IDEMPOTENCY.fullmatch(idempotency_key) is None:
            raise HTTPException(422, "A bounded Idempotency-Key header is required")
        service = get_service()
        run = await _invoke(lambda: service.create(body, idempotency_key=idempotency_key))
        response.headers["ETag"] = f'"{run.revision}"'
        return run

    @router.get("/agent/runs/{run_id}", response_model=AgentRunResponse)
    async def agent_run(
        run_id: str, response: Response,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> AgentRunResponse:
        result = await _invoke(lambda: get_service().get(run_id))
        response.headers["ETag"] = f'"{result.revision}"'
        return result

    @router.get("/agent/runs/{run_id}/results", response_model=AgentRunResultResponse)
    async def agent_run_result(
        run_id: str, response: Response,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> AgentRunResultResponse:
        result = await _invoke(lambda: get_service().result(run_id))
        response.headers["ETag"] = f'"{result.revision}"'
        return result

    @router.get("/agent/runs/{run_id}/evaluation", response_model=AgentEvaluationReport)
    async def agent_run_evaluation(
        run_id: str,
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> AgentEvaluationReport:
        service = get_service()
        run = await _invoke(lambda: service.get(run_id))
        if run.state not in ("succeeded", "failed", "cancelled", "interrupted"):
            raise HTTPException(409, "Agent evaluation requires a terminal run")
        try:
            return await run_in_threadpool(evaluate_durable_agent_run, service, run_id)
        except (JobNotFoundError, JobDataError, WorkspaceDatabaseError, sqlite3.Error, OSError) as error:
            raise _error(error) from error
        except (CorruptAgentSnapshot, ValueError) as error:
            raise HTTPException(503, "Agent evaluation snapshot is unavailable or inconsistent") from error

    @router.post("/agent/runs/{run_id}/cancel", response_model=AgentRunResponse)
    async def cancel_agent_run(
        run_id: str, response: Response,
        if_match: str | None = Header(default=None, alias="If-Match"),
        _grant: AccessGrant = Depends(require_execution_access),
    ) -> AgentRunResponse:
        result = await _invoke(lambda: get_service().cancel(
            run_id, expected_revision=_revision(if_match),
        ))
        response.headers["ETag"] = f'"{result.revision}"'
        return result

    @router.get("/agent/runs/{run_id}/events")
    async def agent_run_events(
        run_id: str, last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        _grant: AccessGrant = Depends(require_local_workspace_access),
    ) -> StreamingResponse:
        events = await _invoke(lambda: get_service().events(
            run_id, after_sequence=_sequence(last_event_id),
        ))
        return StreamingResponse(
            _frames(events), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
