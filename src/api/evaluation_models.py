"""Public, provider-free native metric definition response."""

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
