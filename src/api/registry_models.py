"""Typed API-006 model and dataset registry contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


ModelRole = Literal["generator", "embedding", "reranker"]
ConfigurationStatus = Literal["configured", "not_configured"]
LoadStatus = Literal["loaded", "not_loaded", "unknown"]
AvailabilityStatus = Literal["available", "unavailable", "unknown"]


class ModelRegistryEntry(BaseModel):
    """One stable model role with configuration and runtime facts separated."""

    id: ModelRole
    role: ModelRole
    provider: Literal["groq", "hugging_face"]
    configured_model_id: str | None = None
    configured_revision: str | None = None
    runtime_model_id: str | None = None
    runtime_revision: str | None = None
    configuration_status: ConfigurationStatus
    load_status: LoadStatus
    availability_status: AvailabilityStatus
    availability_reason: str | None = None
    credential_status: Literal["configured", "not_configured", "not_required"]
    test_capabilities: list[Literal["runtime_identity"]]


class ModelRegistryResponse(BaseModel):
    items: list[ModelRegistryEntry]
    total: int = Field(ge=0)


class ModelTestRequest(BaseModel):
    test_type: Literal["runtime_identity"] = "runtime_identity"


class ModelTestCheck(BaseModel):
    id: Literal[
        "configured_identity",
        "runtime_loaded",
        "runtime_identity",
        "runtime_revision",
    ]
    status: Literal["passed", "failed", "unavailable"]
    reason: str | None = None


class ModelTestResponse(BaseModel):
    model_id: ModelRole
    test_type: Literal["runtime_identity"]
    result: Literal["passed", "failed", "unavailable"]
    provider_executed: Literal[False] = False
    checks: list[ModelTestCheck]


DatasetKind = Literal["corpus", "evaluation"]
DatasetAvailability = Literal["available", "degraded", "unavailable"]


class DatasetSummary(BaseModel):
    """One dataset identity without duplicating its canonical data."""

    id: Literal["serving-corpus", "evaluation-test-set"]
    kind: DatasetKind
    name: str
    description: str
    availability: DatasetAvailability
    reason_code: str | None = None
    reason: str | None = None
    version: str | None = None
    revision: str | None = None
    record_count: int | None = Field(default=None, ge=0)
    record_unit: Literal["documents", "cases"]


class DatasetRegistryResponse(BaseModel):
    items: list[DatasetSummary]
    total: int = Field(ge=0)


class DatasetCount(BaseModel):
    key: str
    count: int = Field(ge=0)


class FilingYearCoverage(BaseModel):
    availability: Literal["recorded", "unknown"]
    earliest: int | None = None
    latest: int | None = None
    documents_without_value: int = Field(ge=0)
    reason: str | None = None


class CorpusDatasetCoverage(BaseModel):
    kind: Literal["corpus"] = "corpus"
    documents: int = Field(ge=0)
    companies: int = Field(ge=0)
    chunks: int = Field(ge=0)
    configured_companies: int = Field(ge=0)
    configured_companies_with_documents: list[str]
    configured_companies_without_documents: list[str]
    filing_years: FilingYearCoverage
    sections: list[DatasetCount]


class EvaluationDatasetCoverage(BaseModel):
    kind: Literal["evaluation"] = "evaluation"
    cases: int = Field(ge=0)
    categories: list[DatasetCount]
    priorities: list[DatasetCount]
    tickers: list[str]
    sections: list[str]


DatasetCoverage = Annotated[
    CorpusDatasetCoverage | EvaluationDatasetCoverage,
    Field(discriminator="kind"),
]


class DatasetProvenance(BaseModel):
    authority: Literal["qdrant_index_manifest", "built_in_evaluation_test_set"]
    status: Literal["consistent", "recorded", "missing", "invalid", "mismatch"]
    reason_code: str | None = None
    reason: str | None = None
    schema_version: int | None = None
    revision: str | None = None
    build_version: str | None = None
    collection_name: str | None = None
    point_count: int | None = Field(default=None, ge=0)
    embedding_model_id: str | None = None
    embedding_model_revision: str | None = None
    vector_dimension: int | None = Field(default=None, ge=1)
    distance_metric: str | None = None
    snapshot_id: str | None = None
    embedding_generation_id: str | None = None
    embedding_generation_fingerprint: str | None = None


class DatasetDetail(DatasetSummary):
    coverage: DatasetCoverage | None = None
    provenance: DatasetProvenance
