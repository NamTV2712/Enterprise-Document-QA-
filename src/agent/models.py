"""Typed Agent inputs and observations; source text remains untrusted data."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas import (
    DiscoverySnapshotResponse,
    QueryInterpretation, QueryRequest,
    QueryResponse,
    RetrievalInspectRequest,
    SearchRequest,
)


class SearchDocumentsInput(SearchRequest):
    model_config = ConfigDict(extra="forbid", strict=True)
    section: Literal["business", "risk_factors", "mdna", "financial_statements", "financial_table"] | None = None
    filing_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class InspectRetrievalInput(RetrievalInspectRequest):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReadDocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    document_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class AskRagInput(QueryRequest):
    model_config = ConfigDict(extra="forbid", strict=True)
    # Agent calls are stateless. Conversation mutation belongs to the future run owner.
    session_id: None = None


class RetrievalCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")
    chunk_id: str
    document_id: str | None = None
    citation: str | None = None
    text_preview: str = ""
    bm25_score: float | None = None
    dense_score: float | None = None
    rrf_score: float | None = None
    cross_encoder_score: float | None = None
    selected: bool = False


class RetrievalStage(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    status: Literal["executed", "skipped", "not_executed"]
    elapsed_ms: float | None = None
    reason: str | None = None


class RetrievalTrace(BaseModel):
    model_config = ConfigDict(extra="allow")
    trace_version: str
    preset: str
    candidates: list[RetrievalCandidate]
    stages: list[RetrievalStage]
    selected_chunk_ids: list[str]
    candidate_count: int
    selected_count: int
    score_semantics: dict[str, Any]


class RetrievalObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_interpretation: QueryInterpretation
    trace: RetrievalTrace


class DocumentChunkPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str | None
    section: str | None = None
    text_preview: str
    text_length: int


class DocumentObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    ticker: str | None = None
    filing_date: str | None = None
    report_date: str | None = None
    sections: list[str]
    chunk_count: int
    items: list[DocumentChunkPreview]
    total: int
    page: int
    page_size: int
    representation: Literal["indexed_chunk_previews"] = "indexed_chunk_previews"
    full_source_in_observation: bool = False


class ToolObservation(BaseModel):
    """The label prevents evidence text from being promoted into tool authority."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    tool_name: str
    content_trust: Literal["untrusted_data"] = "untrusted_data"
    data: DiscoverySnapshotResponse | RetrievalObservation | DocumentObservation | QueryResponse
