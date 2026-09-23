"""Explicit public schemas for native definitions and read-only analytics."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NativeMetricDefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metric_id: str
    metric_version: int = Field(ge=1)
    label: str
    meaning: str
    value_kind: Literal["ratio", "boolean"]
    aggregate_kind: Literal["mean", "success_rate"]
    direction: Literal["higher_is_better"]
    source: Literal["precomputed_native_judge", "deterministic"]
    minimum: float
    maximum: float
    required_inputs: list[str]


class EvaluationMetricCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    provider_free: Literal[True]
    computes_judge_scores: Literal[False]
    requires_bound_judge_scores: Literal[True]


class EvaluationMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    protocol: Literal["native-evaluation"]
    protocol_version: Literal[1]
    capabilities: EvaluationMetricCapabilities
    items: list[NativeMetricDefinitionModel]
    total: int = Field(ge=0)


class NativeBindingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    engine_id: Literal["native"]
    engine_version: int
    dataset_id: str
    dataset_version: str
    dataset_revision: str
    generator_model_id: str
    generator_model_fingerprint: str
    generation_prompt_sha256: str
    generation_binding: str
    retrieval_binding: str
    retrieval_config_fingerprint: str
    embedding_fingerprint: str
    reranker_fingerprint: str
    context_binding: str
    judge_model_id: str | None
    judge_prompt_sha256: str | None
    judge_binding: str | None


class NativeCaseMetricModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metric_id: str
    metric_version: int
    status: Literal["computed", "unavailable", "not_applicable"]
    value: float | bool | None
    reason_code: str | None


class NativeAggregateMetricModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metric_id: str
    metric_version: int
    status: Literal["computed", "unavailable", "not_applicable"]
    value: float | None
    total_cases: int
    denominator: int
    unavailable_count: int
    not_applicable_count: int


class NativeCaseResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    case_id: str
    context_sha256: str | None
    metrics: list[NativeCaseMetricModel]


class NativePublishedSummaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    protocol: Literal["native-evaluation"]
    protocol_version: Literal[1]
    run_id: str
    status: Literal["complete", "incomplete"]
    published_at: str
    report_digest: str
    case_count: int
    binding: NativeBindingModel
    aggregates: list[NativeAggregateMetricModel]


class NativePublishedDetailModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    published_at: str
    protocol: Literal["native-evaluation"]
    protocol_version: Literal[1]
    run_id: str
    status: Literal["complete", "incomplete"]
    report_digest: str
    case_count: int
    binding: NativeBindingModel
    metric_definitions: list[NativeMetricDefinitionModel]
    aggregates: list[NativeAggregateMetricModel]


class NativeResultsPageModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str
    report_digest: str
    report_status: Literal["complete", "incomplete"]
    metric_definitions: list[NativeMetricDefinitionModel]
    aggregates: list[NativeAggregateMetricModel]
    items: list[NativeCaseResultModel]
    total: int
    page: int
    page_size: int


class NativeCompareRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    baseline_run_id: str = Field(min_length=1, max_length=128)
    candidate_run_id: str = Field(min_length=1, max_length=128)
    metric_ids: list[str] | None = Field(default=None, max_length=6)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class NativeMetricComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metric_id: str
    metric_version: int
    direction: Literal["higher_is_better", "lower_is_better"]
    baseline: NativeAggregateMetricModel
    candidate: NativeAggregateMetricModel
    same_computed_case_coverage: bool
    status: Literal["comparable", "unavailable", "not_applicable", "incompatible"]
    candidate_minus_baseline: float | None
    reason_code: str | None


class NativeCaseMetricComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metric_id: str
    metric_version: int
    baseline: NativeCaseMetricModel | None
    candidate: NativeCaseMetricModel | None
    status: Literal["comparable", "unavailable", "not_applicable", "incompatible", "unpaired"]
    candidate_minus_baseline: float | None
    reason_code: str | None


class NativeCaseComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    case_id: str
    pairing: Literal["paired", "baseline_only", "candidate_only"]
    baseline_context_sha256: str | None
    candidate_context_sha256: str | None
    metrics: list[NativeCaseMetricComparisonModel]


class NativeCompareResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    baseline_run_id: str
    candidate_run_id: str
    baseline_digest: str
    candidate_digest: str
    baseline_status: Literal["complete", "incomplete"]
    candidate_status: Literal["complete", "incomplete"]
    baseline_binding: NativeBindingModel
    candidate_binding: NativeBindingModel
    same_case_universe: bool
    eligible_for_complete_comparison: bool
    eligibility_reasons: list[str]
    metrics: list[NativeMetricComparisonModel]
    cases: list[NativeCaseComparisonModel]
    total_cases: int
    page: int
    page_size: int


class NativeTrendPointModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str
    report_digest: str
    published_at: str
    report_status: Literal["complete", "incomplete"]
    aggregate: NativeAggregateMetricModel
    generator_model_id: str
    generation_binding: str
    retrieval_binding: str
    judge_binding: str | None


class NativeTrendGroupModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    binding_group: str
    metric_id: str
    metric_version: int
    points: list[NativeTrendPointModel]


class NativeTrendsResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metric_id: str
    groups: list[NativeTrendGroupModel]
    total_points: int
    page: int
    page_size: int


class NativeFailureFindingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    category_id: str
    case_id: str
    context_sha256: str | None
    metric_id: str
    metric_version: int
    metric_status: Literal["computed", "unavailable"]
    value: float | bool | None
    reason_code: str | None


class NativeFailureCategoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    category_id: str
    count: int


class NativeFailuresResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str
    report_digest: str
    report_status: Literal["complete", "incomplete"]
    category_counts: list[NativeFailureCategoryModel]
    items: list[NativeFailureFindingModel]
    total: int
    page: int
    page_size: int
