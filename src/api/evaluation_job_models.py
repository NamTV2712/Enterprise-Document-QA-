"""Private EVAL-003 request and response contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.workspace.jobs import JobState, JobStepState
from src.api.evaluation_models import (
    NativeBindingModel, NativeCaseMetricModel, NativeMetricDefinitionModel,
    NativeAggregateMetricModel,
)


NativeMetricId = Literal[
    "native.faithfulness", "native.answer_relevancy", "native.context_precision",
    "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness",
]


class EvaluationJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    artifact_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    engine: Literal["native"]
    metrics: list[NativeMetricId] = Field(min_length=6, max_length=6)
    mode: Literal["provider_backed"]
    budget: int = Field(ge=1, le=15000)


class EvaluationJobProgress(BaseModel):
    stage: str | None
    current: int | None
    total: int | None


class EvaluationJobStep(BaseModel):
    step_id: str
    job_id: str
    ordinal: int
    name: str
    state: JobStepState
    revision: int
    started_at: str | None
    finished_at: str | None


class FrozenEvaluationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    request_fingerprint: str
    protocol: Literal["native-evaluation"]
    protocol_version: Literal[1]
    engine: Literal["native"]
    engine_version: Literal[1]
    mode: Literal["provider_backed"]
    metric_versions: dict[str, int]
    metric_definitions_digest: str
    artifact_id: str
    artifact_digest: str
    retrieval_fingerprints: dict[str, str | int | None]
    case_ids: list[str]
    case_hashes: list[str]
    context_hashes: list[str]
    budget_unit: Literal["provider_attempt_slot"]
    budget_limit: int
    maximum_required_attempts: int
    binding: NativeBindingModel
    generation_system_prompt_sha256: str
    generation_context_builder_fingerprint: str
    answer_completion_fingerprint: str
    answer_postprocessor_profile_sha256: str
    generation_prompt_template_sha256: str
    judge_system_prompt_sha256: str
    judge_context_builder_fingerprint: str
    judge_max_tokens: int
    runtime_code_fingerprints: dict[str, str]
    runtime_source_digest: str
    judge_prompt_template_sha256: str
    snapshot_digest: str


class EvaluationJobResult(BaseModel):
    report_digest: str
    budget_consumed: int


class EvaluationJobFailure(BaseModel):
    code: str
    message: str


class EvaluationJobResponse(BaseModel):
    id: str
    state: JobState
    revision: int
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
    cancellation_requested_at: str | None
    configuration_fingerprint: str
    frozen: FrozenEvaluationSnapshot
    progress: EvaluationJobProgress
    steps: list[EvaluationJobStep]
    artifact_references: list[str]
    budget_consumed: int
    publication_status: Literal["not_published"]
    report_digest: str | None
    result: EvaluationJobResult | None
    failure: EvaluationJobFailure | None


class EvaluationJobPage(BaseModel):
    items: list[EvaluationJobResponse]
    total: int
    page: int
    page_size: int


class PrivateNativeCaseInput(BaseModel):
    case_id: str
    answer: str | None
    rendered_context: str | None
    ground_truth: str | None
    required_keywords: list[str] | None
    expects_fallback: bool | None
    judge_scores: dict[str, float] | None
    generation_context_sha256: str | None
    judge_context_sha256: str | None
    generation_binding: str | None
    judge_binding: str | None


class PrivateEvaluationCase(BaseModel):
    case_id: str
    question: str
    input: PrivateNativeCaseInput
    metrics: list[NativeCaseMetricModel]
    judge_prompt_sha256: str


class EvaluationCasePage(BaseModel):
    job_id: str
    items: list[PrivateEvaluationCase]
    total: int
    page: int
    page_size: int
    report_status: Literal["complete", "incomplete"] | None
    report_digest: str | None
    metric_definitions: list[NativeMetricDefinitionModel]
    aggregates: list[NativeAggregateMetricModel]
