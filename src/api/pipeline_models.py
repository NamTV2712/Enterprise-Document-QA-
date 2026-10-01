"""Typed API-007 pipeline-definition and staged-run contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from configs.tickers import TICKERS
from src.workspace.jobs import JobState, JobStepState


TickerId = Annotated[
    str,
    Field(min_length=1, max_length=5, pattern=r"^[A-Z]{1,5}(?:-[A-Z])?$"),
]
PipelineStageId = Literal[
    "download_filings",
    "chunk_filings",
    "add_table_chunks",
    "embed_chunks",
    "index_chunks",
]
PipelineId = Literal["sec_10k_ingestion"]
StagingProfileId = Literal["isolated"]
PipelineEventType = Literal[
    "created",
    "state_changed",
    "progress",
    "step_changed",
    "cancellation_requested",
    "cancelled",
    "interrupted",
]


class PipelineStageDefinition(BaseModel):
    stage_id: PipelineStageId
    order: int = Field(ge=1)
    description: str


class PipelineCapabilities(BaseModel):
    can_stage: Literal[True] = True
    can_cancel: Literal[True] = True
    event_transport: Literal["sse"] = "sse"
    executes_during_staging: Literal[False] = False
    automatically_promotes_to_serving: Literal[False] = False


class PipelineDefinitionResponse(BaseModel):
    pipeline_id: PipelineId
    name: str
    input_kind: Literal["ticker"] = "ticker"
    registered_input_ids: list[TickerId]
    staging_profiles: list[StagingProfileId]
    stages: list[PipelineStageDefinition]
    capabilities: PipelineCapabilities


class PipelineRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    input_ids: list[TickerId] = Field(min_length=1, max_length=len(TICKERS))
    staging_profile: StagingProfileId


class PipelineProgressResponse(BaseModel):
    stage: PipelineStageId | None = None
    current: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=1)


class PipelineFailureResponse(BaseModel):
    code: str
    message: str


class PipelineStepResponse(BaseModel):
    step_id: str
    stage_id: PipelineStageId
    state: JobStepState
    revision: int = Field(ge=1)
    started_at: str | None = None
    finished_at: str | None = None


class PipelineRunResponse(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    pipeline_id: PipelineId
    state: JobState
    revision: int = Field(ge=1)
    configuration_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    input_ids: list[TickerId]
    staging_profile: StagingProfileId
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    cancellation_requested_at: str | None = None
    progress: PipelineProgressResponse
    steps: list[PipelineStepResponse]
    artifact_references: list[str]
    failure: PipelineFailureResponse | None = None


class PipelineRunPageResponse(BaseModel):
    items: list[PipelineRunResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class PipelineRunEventResponse(BaseModel):
    run_id: str
    event_id: str
    sequence: int = Field(ge=1)
    event_type: PipelineEventType
    state: JobState | None = None
    reason_code: str | None = None
    progress: PipelineProgressResponse
    occurred_at: str
