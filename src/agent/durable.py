"""DATA-004 ownership around the existing bounded Agent orchestrator."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable

from pydantic import ValidationError

from src.agent.decision import AgentDecisionModel, DecisionProviderUnavailable
from src.agent.durable_models import (
    AgentDurableResult, AgentEventSummary, AgentRunCreateRequest, AgentRunEventResponse,
    AgentRunFailure, AgentRunPage, AgentRunResponse, AgentRunResultResponse,
    AgentRunStep, FrozenAgentPlan,
)
from src.agent.orchestration import AgentOrchestrator
from src.agent.policies import AgentExecutionContext, ToolPolicy
from src.agent.registry import AgentToolRegistry
from src.agent.state import AgentResult, AgentRunPolicy, AgentTraceEntry
from src.workspace.jobs import (
    AgentJobEvent, DurableJob, JobConflictError, JobDataError, JobNotFoundError,
    JobState, JobTransitionError, SQLiteJobRepository,
)


AGENT_JOB_TYPE = "bounded_agent_run"
AGENT_STEP = "execute_agent"
MAX_AGENT_RESULT_BYTES = 8 * 1024
_RUN_ID = re.compile(r"^agent_([A-Za-z0-9_-]{1,122})$")


class _UnavailableDecisionModel:
    requires_provider = False

    async def decide(self, _request: object) -> object:
        raise DecisionProviderUnavailable


class _DurableCancellationSignal:
    def __init__(self, repository: SQLiteJobRepository, job_id: str) -> None:
        self.repository = repository
        self.job_id = job_id

    def is_set(self) -> bool:
        return self.repository.get_job(self.job_id).state != "running"


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _run_id(job_id: str) -> str:
    if not job_id.startswith("job_"):
        raise JobDataError("Agent job identity is invalid")
    return "agent_" + job_id[4:]


def _job_id(run_id: str) -> str:
    match = _RUN_ID.fullmatch(run_id)
    if match is None:
        raise JobNotFoundError("Agent run does not exist")
    return "job_" + match.group(1)


def _durable_result(result: AgentResult, *, cancelled: bool = False) -> AgentDurableResult:
    payload = AgentDurableResult(
        agent_status="cancelled" if cancelled else result.status,
        answer=None if cancelled else result.answer,
        evidence_refs=() if cancelled else result.evidence_refs,
        step_count=result.step_count, decision_call_count=result.decision_call_count,
        tool_call_count=result.tool_call_count, per_tool_calls=dict(result.per_tool_calls),
        observation_count=len(result.observations),
        failure=result.failure if not cancelled else None,
        research=result.research,
    )
    if len(_canonical_json(payload.model_dump(mode="json"))) > MAX_AGENT_RESULT_BYTES:
        raise ValueError("bounded Agent result exceeds durable byte limit")
    return payload


class AgentDurableService:
    """Create, claim, inspect and finish one DATA-004-backed Agent run."""

    def __init__(
        self, repository: SQLiteJobRepository, registry_factory: Callable[[], AgentToolRegistry],
        *, decision_model_factory: Callable[[str], AgentDecisionModel] | None = None,
        decision_model_id: str = "unconfigured",
    ) -> None:
        self.repository = repository
        self.registry_factory = registry_factory
        self.decision_model_factory = decision_model_factory
        if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", decision_model_id) is None:
            raise ValueError("decision model identity is invalid")
        self.decision_model_id = decision_model_id

    def _plan(self, body: AgentRunCreateRequest) -> FrozenAgentPlan:
        return FrozenAgentPlan(
            decision_model_id=self.decision_model_id, goal=body.goal.strip(),
            locale=body.locale, allowed_tools=tuple(body.allowed_tools),
            allow_provider_tool_execution=body.allow_provider_tool_execution,
            allow_decision_provider_execution=body.allow_decision_provider_execution,
            require_observation_for_final=body.require_observation_for_final,
            reject_duplicate_calls=body.reject_duplicate_calls,
            limits=AgentRunCreateRequest.model_validate(body.model_dump()).limits,
            research=body.research,
        )

    def create(self, body: AgentRunCreateRequest, *, idempotency_key: str) -> AgentRunResponse:
        plan = self._plan(body)
        encoded = plan.model_dump(mode="json", exclude_none=True)
        fingerprint = hashlib.sha256(_canonical_json(encoded)).hexdigest()
        job = self.repository.create_job(
            namespace="agent", job_type=AGENT_JOB_TYPE,
            idempotency_key=idempotency_key, configuration_fingerprint=fingerprint,
            payload=encoded, steps=(AGENT_STEP,),
        )
        return self._view(job)

    def _job(self, run_id: str) -> DurableJob:
        job = self.repository.get_job(_job_id(run_id))
        if job.namespace != "agent" or job.job_type != AGENT_JOB_TYPE:
            raise JobNotFoundError("Agent run does not exist")
        return job

    @staticmethod
    def _frozen(job: DurableJob) -> FrozenAgentPlan:
        try:
            plan = FrozenAgentPlan.model_validate(job.payload)
            if hashlib.sha256(_canonical_json(plan.model_dump(mode="json", exclude_none=True))).hexdigest() != job.configuration_fingerprint:
                raise ValueError("frozen Agent fingerprint mismatch")
            if len(job.steps) != 1 or job.steps[0].name != AGENT_STEP:
                raise ValueError("Agent durable step is invalid")
            return plan
        except (ValidationError, TypeError, ValueError) as error:
            raise JobDataError("persisted Agent plan is invalid") from error

    @staticmethod
    def _stored_result(job: DurableJob) -> AgentDurableResult | None:
        if job.result is None:
            return None
        try:
            if len(_canonical_json(job.result)) > MAX_AGENT_RESULT_BYTES:
                raise ValueError("Agent result exceeds byte limit")
            return AgentDurableResult.model_validate(job.result)
        except (ValidationError, TypeError, ValueError) as error:
            raise JobDataError("persisted Agent result is invalid") from error

    def _view(self, job: DurableJob) -> AgentRunResponse:
        plan = self._frozen(job)
        result = self._stored_result(job)
        step = job.steps[0]
        return AgentRunResponse(
            run_id=_run_id(job.job_id), state=job.state, revision=job.revision,
            configuration_fingerprint=job.configuration_fingerprint,
            frozen=plan, created_at=job.created_at, updated_at=job.updated_at,
            started_at=job.started_at, finished_at=job.finished_at,
            cancellation_requested_at=job.cancellation_requested_at,
            progress_current=job.progress.current, progress_total=job.progress.total,
            step=AgentRunStep(name=AGENT_STEP, state=step.state, revision=step.revision,
                              started_at=step.started_at, finished_at=step.finished_at),
            result=result,
            failure=AgentRunFailure(code=job.failure_code, message=job.failure_message)
            if job.failure_code and job.failure_message else None,
        )

    def get(self, run_id: str) -> AgentRunResponse:
        return self._view(self._job(run_id))

    def list(self, *, state: JobState | None, page: int, page_size: int) -> AgentRunPage:
        rows = self.repository.list_jobs(
            namespace="agent", state=state, limit=page_size, offset=(page - 1) * page_size,
        )
        return AgentRunPage(items=[self._view(job) for job in rows.items],
                            total=rows.total, page=page, page_size=page_size)

    def result(self, run_id: str) -> AgentRunResultResponse:
        view = self.get(run_id)
        return AgentRunResultResponse(
            run_id=view.run_id, state=view.state, revision=view.revision,
            result=view.result, failure=view.failure,
        )

    def cancel(self, run_id: str, *, expected_revision: int) -> AgentRunResponse:
        job = self._job(run_id)
        return self._view(self.repository.request_cancellation(
            job.job_id, expected_revision=expected_revision,
        ))

    def events(self, run_id: str, *, after_sequence: int) -> tuple[AgentRunEventResponse, ...]:
        job = self._job(run_id)
        rows = self.repository.list_agent_events(job.job_id, after_sequence=after_sequence, limit=100)
        return tuple(self._event_view(run_id, row) for row in rows)

    @staticmethod
    def _event_view(run_id: str, row: AgentJobEvent) -> AgentRunEventResponse:
        try:
            summary = AgentEventSummary.model_validate(row.payload) if row.payload else None
        except ValidationError as error:
            raise JobDataError("persisted Agent event summary is invalid") from error
        return AgentRunEventResponse(
            run_id=run_id, event_id=row.event_id, sequence=row.sequence,
            event_type=row.event_type, state=row.state, reason_code=row.reason_code,
            occurred_at=row.occurred_at, summary=summary,
        )

    async def _record_trace(
        self, job_id: str, entry: AgentTraceEntry, step_count: int,
        tool_call_count: int, max_steps: int,
    ) -> None:
        summary = AgentEventSummary(
            decision_index=entry.decision_index, decision_kind=entry.kind,
            tool_name=entry.tool_name, objective_id=entry.objective_id,
            argument_names=list(entry.argument_names),
            outcome=entry.outcome, evidence_count=len(entry.evidence_refs),
            evidence_refs=list(entry.evidence_refs[:8]), step_count=step_count,
            tool_call_count=tool_call_count, failure_code=entry.failure_code,
        )
        await asyncio.to_thread(
            self.repository.append_agent_decision_event, job_id,
            event_key=f"decision_{entry.decision_index}",
            payload=summary.model_dump(mode="json"),
            step_count=step_count, max_steps=max_steps,
        )

    def _finish(self, job_id: str, result: AgentResult) -> None:
        # A concurrent cancellation can win after the last Agent boundary.
        # Re-read before each transition and let DATA-004 decide the state.
        for _ in range(3):
            current = self.repository.get_job(job_id)
            try:
                if current.state == "cancelling":
                    self.repository.acknowledge_cancellation(
                        job_id, expected_revision=current.revision,
                        result=_durable_result(result, cancelled=True).model_dump(mode="json"),
                    )
                    return
                if current.state != "running":
                    return
                durable = _durable_result(result)
                if result.status == "completed":
                    current = self.repository.transition_step(
                        job_id, current.steps[0].step_id,
                        expected_job_revision=current.revision,
                        expected_step_revision=current.steps[0].revision,
                        target_state="succeeded",
                    )
                    self.repository.transition_job(
                        job_id, expected_revision=current.revision, target_state="succeeded",
                        result=durable.model_dump(mode="json"),
                    )
                else:
                    failure_code = result.failure.code if result.failure else "agent_execution_failed"
                    self.repository.transition_job(
                        job_id, expected_revision=current.revision, target_state="failed",
                        result=durable.model_dump(mode="json"), failure_code=failure_code,
                        failure_message="Agent execution ended without a completed answer.",
                    )
                return
            except (JobConflictError, JobTransitionError):
                continue
        raise JobConflictError("Agent terminal revision conflict")

    async def run(self, run_id: str) -> AgentRunResponse:
        """One atomic claim; never replay a run already claimed or interrupted."""
        job = self._job(run_id)
        if job.state != "queued":
            return self._view(job)
        try:
            job = self.repository.transition_job(
                job.job_id, expected_revision=job.revision, target_state="running",
            )
        except (JobConflictError, JobTransitionError):
            return self.get(run_id)
        try:
            plan = self._frozen(job)
            job = self.repository.transition_step(
                job.job_id, job.steps[0].step_id,
                expected_job_revision=job.revision,
                expected_step_revision=job.steps[0].revision, target_state="running",
            )
            try:
                model = (
                    self.decision_model_factory(plan.decision_model_id)
                    if self.decision_model_factory is not None else None
                )
            except Exception:
                model = None
            if model is None or type(getattr(model, "requires_provider", None)) is not bool:
                model = _UnavailableDecisionModel()
            orchestrator = AgentOrchestrator(
                self.registry_factory(), model, limits=plan.limits,
                policy=AgentRunPolicy(
                    allow_decision_provider_execution=plan.allow_decision_provider_execution,
                    require_observation_for_final=plan.require_observation_for_final,
                    reject_duplicate_calls=plan.reject_duplicate_calls,
                ),
                research=plan.research,
            )
            context = AgentExecutionContext(
                ToolPolicy(frozenset(plan.allowed_tools), plan.allow_provider_tool_execution),
                request_id=run_id, locale=plan.locale,
            )
            result = await orchestrator.run(
                plan.goal, context,
                cancel_event=_DurableCancellationSignal(self.repository, job.job_id),
                trace_sink=lambda entry, steps, tools: self._record_trace(
                    job.job_id, entry, steps, tools, plan.limits.max_steps,
                ),
            )
            self._finish(job.job_id, result)
        except Exception:
            # A failed DB write may leave the run active; startup recovery will
            # mark it interrupted. Never replay a possibly completed provider call.
            for _ in range(3):
                current = self.repository.get_job(job.job_id)
                try:
                    if current.state == "cancelling":
                        self.repository.acknowledge_cancellation(
                            job.job_id, expected_revision=current.revision,
                        )
                    elif current.state == "running":
                        self.repository.transition_job(
                            job.job_id, expected_revision=current.revision,
                            target_state="failed", failure_code="agent_execution_failed",
                            failure_message="Agent execution stopped before terminal result commit.",
                        )
                    break
                except (JobConflictError, JobTransitionError):
                    continue
        return self.get(run_id)
