"""Provider-free API-007 staging over the DATA-004 durable-job repository."""

from __future__ import annotations

import hashlib
import json
import re

from pydantic import ValidationError

from configs.settings import Settings
from configs.tickers import TICKERS
from src.api.pipeline_models import (
    PipelineDefinitionResponse,
    PipelineFailureResponse,
    PipelineProgressResponse,
    PipelineRunCreateRequest,
    PipelineRunEventResponse,
    PipelineRunPageResponse,
    PipelineRunResponse,
    PipelineStageDefinition,
    PipelineStepResponse,
)
from src.workspace.jobs import (
    DurableJob,
    JobEvent,
    JobDataError,
    JobNotFoundError,
    JobState,
    SQLiteJobRepository,
)


PIPELINE_ID = "sec_10k_ingestion"
PIPELINE_JOB_TYPE = PIPELINE_ID
STAGING_PROFILE = "isolated"
MAX_PAGE_SIZE = 100
MAX_EVENTS_PER_RESPONSE = 100
MAX_EVENT_SEQUENCE = 9_223_372_036_854_775_807
_OPAQUE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

PIPELINE_STAGES: tuple[PipelineStageDefinition, ...] = (
    PipelineStageDefinition(
        stage_id="download_filings",
        order=1,
        description="Acquire the latest configured SEC filing and extract sections.",
    ),
    PipelineStageDefinition(
        stage_id="chunk_filings",
        order=2,
        description="Build filing chunks from extracted sections.",
    ),
    PipelineStageDefinition(
        stage_id="add_table_chunks",
        order=3,
        description="Add supplemental financial-table chunks before embedding.",
    ),
    PipelineStageDefinition(
        stage_id="embed_chunks",
        order=4,
        description="Build an immutable embedding generation from staged chunks.",
    ),
    PipelineStageDefinition(
        stage_id="index_chunks",
        order=5,
        description="Build and verify an index for the staged embedding generation.",
    ),
)


class PipelineInputNotFoundError(RuntimeError):
    """A request named an input that is not in the configured ticker registry."""


class PipelineRequestError(ValueError):
    """A typed staging request is internally inconsistent."""


class PipelineDataError(JobDataError):
    """A persisted job cannot be safely projected as a pipeline run."""


def validate_pipeline_request(body: PipelineRunCreateRequest) -> None:
    """Validate configured inputs without opening the private workspace."""
    if body.staging_profile != STAGING_PROFILE:
        raise PipelineRequestError("unsupported pipeline staging profile")
    if len(set(body.input_ids)) != len(body.input_ids):
        raise PipelineRequestError("pipeline input IDs must be unique")
    if any(ticker not in TICKERS for ticker in body.input_ids):
        raise PipelineInputNotFoundError("pipeline input ID is not registered")


def pipeline_definition() -> PipelineDefinitionResponse:
    """Return static registered capability without opening the workspace."""
    return PipelineDefinitionResponse(
        pipeline_id=PIPELINE_ID,
        name="SEC 10-K ingestion",
        registered_input_ids=list(TICKERS),
        staging_profiles=[STAGING_PROFILE],
        stages=list(PIPELINE_STAGES),
        capabilities={
            "can_stage": True,
            "can_cancel": True,
            "event_transport": "sse",
            "executes_during_staging": False,
            "automatically_promotes_to_serving": False,
        },
    )


class PipelineService:
    """Project API-level run views and stage-only requests onto DATA-004."""

    def __init__(self, repository: SQLiteJobRepository, configured: Settings) -> None:
        self.repository = repository
        self._configured = configured

    def _configuration_fingerprint(self) -> str:
        binding = {
            "pipeline_id": PIPELINE_ID,
            "definition_revision": 1,
            "staging_profile": STAGING_PROFILE,
            "stages": [stage.stage_id for stage in PIPELINE_STAGES],
            "table_enrichment_before_embedding": True,
            "embedding_model_id": self._configured.embedding_model_id,
            "embedding_model_revision": self._configured.embedding_model_revision or None,
        }
        canonical = json.dumps(binding, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_request_key(
        body: PipelineRunCreateRequest,
        configuration_fingerprint: str,
    ) -> str:
        identity = {
            "pipeline_id": PIPELINE_ID,
            "input_ids": body.input_ids,
            "staging_profile": body.staging_profile,
            "configuration_fingerprint": configuration_fingerprint,
        }
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def stage(self, body: PipelineRunCreateRequest) -> PipelineRunResponse:
        validate_pipeline_request(body)

        configuration_fingerprint = self._configuration_fingerprint()
        job = self.repository.create_job(
            namespace="pipeline",
            job_type=PIPELINE_JOB_TYPE,
            idempotency_key=self._canonical_request_key(
                body,
                configuration_fingerprint,
            ),
            configuration_fingerprint=configuration_fingerprint,
            payload={
                "pipeline_id": PIPELINE_ID,
                "input_ids": list(body.input_ids),
                "staging_profile": body.staging_profile,
            },
            steps=tuple(stage.stage_id for stage in PIPELINE_STAGES),
        )
        return self._run_response(job)

    def list_runs(
        self,
        *,
        state: JobState | None,
        page: int,
        page_size: int,
    ) -> PipelineRunPageResponse:
        if page < 1:
            raise ValueError("page must be positive")
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError("page size is out of bounds")
        offset = (page - 1) * page_size
        first = self.repository.list_jobs(
            namespace="pipeline",
            state=state,
            limit=1,
            offset=0,
        )
        if offset >= first.total:
            return PipelineRunPageResponse(
                items=[],
                total=first.total,
                page=page,
                page_size=page_size,
            )
        result = self.repository.list_jobs(
            namespace="pipeline",
            state=state,
            limit=page_size,
            offset=offset,
        )
        runs = [self._run_response(job) for job in result.items]
        return PipelineRunPageResponse(
            items=runs,
            total=result.total,
            page=page,
            page_size=page_size,
        )

    def get_run(self, run_id: str) -> PipelineRunResponse:
        job = self._job_or_404(run_id)
        return self._run_response(job)

    def cancel_run(self, run_id: str, *, expected_revision: int) -> PipelineRunResponse:
        job = self._job_or_404(run_id)
        return self._run_response(
            self.repository.request_cancellation(
                job.job_id,
                expected_revision=expected_revision,
            )
        )

    def list_events(
        self,
        run_id: str,
        *,
        after_sequence: int,
    ) -> tuple[PipelineRunEventResponse, ...]:
        job = self._job_or_404(run_id)
        events = self.repository.list_events(
            job.job_id,
            after_sequence=after_sequence,
            limit=MAX_EVENTS_PER_RESPONSE,
        )
        return tuple(self._event_response(event) for event in events)

    def _job_or_404(self, run_id: str) -> DurableJob:
        if not _OPAQUE_JOB_ID.fullmatch(run_id):
            raise JobNotFoundError("pipeline run does not exist")
        job = self.repository.get_job(run_id)
        if job.namespace != "pipeline" or job.job_type != PIPELINE_JOB_TYPE:
            raise JobNotFoundError("pipeline run does not exist")
        return job

    @staticmethod
    def _run_response(job: DurableJob) -> PipelineRunResponse:
        expected_steps = tuple(stage.stage_id for stage in PIPELINE_STAGES)
        if (
            job.namespace != "pipeline"
            or job.job_type != PIPELINE_JOB_TYPE
            or set(job.payload) != {"pipeline_id", "input_ids", "staging_profile"}
            or job.payload.get("pipeline_id") != PIPELINE_ID
            or tuple(step.name for step in job.steps) != expected_steps
        ):
            raise PipelineDataError("persisted pipeline run is invalid")
        if (job.failure_code is None) != (job.failure_message is None):
            raise PipelineDataError("persisted pipeline failure is incomplete")

        try:
            payload = PipelineRunCreateRequest.model_validate(
                {
                    "input_ids": job.payload.get("input_ids"),
                    "staging_profile": job.payload.get("staging_profile"),
                }
            )
            validate_pipeline_request(payload)
            failure = (
                PipelineFailureResponse(
                    code=job.failure_code,
                    message=job.failure_message,
                )
                if job.failure_code is not None and job.failure_message is not None
                else None
            )
            return PipelineRunResponse(
                id=job.job_id,
                pipeline_id=PIPELINE_ID,
                state=job.state,
                revision=job.revision,
                configuration_fingerprint=job.configuration_fingerprint,
                input_ids=payload.input_ids,
                staging_profile=payload.staging_profile,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
                cancellation_requested_at=job.cancellation_requested_at,
                progress=PipelineProgressResponse(
                    stage=job.progress.stage,
                    current=job.progress.current,
                    total=job.progress.total,
                ),
                steps=[
                    PipelineStepResponse(
                        step_id=step.step_id,
                        stage_id=step.name,
                        state=step.state,
                        revision=step.revision,
                        started_at=step.started_at,
                        finished_at=step.finished_at,
                    )
                    for step in job.steps
                ],
                artifact_references=list(job.artifact_references),
                failure=failure,
            )
        except (
            ValidationError,
            PipelineInputNotFoundError,
            PipelineRequestError,
            TypeError,
            ValueError,
        ) as error:
            raise PipelineDataError("persisted pipeline run is invalid") from error

    @staticmethod
    def _event_response(event: JobEvent) -> PipelineRunEventResponse:
        try:
            return PipelineRunEventResponse(
                run_id=event.job_id,
                event_id=event.event_id,
                sequence=event.sequence,
                event_type=event.event_type,
                state=event.state,
                reason_code=event.reason_code,
                progress=PipelineProgressResponse(
                    stage=event.progress.stage,
                    current=event.progress.current,
                    total=event.progress.total,
                ),
                occurred_at=event.occurred_at,
            )
        except (ValidationError, TypeError, ValueError) as error:
            raise PipelineDataError("persisted pipeline event is invalid") from error
