"""Stable request and response models for the existing HTTP API."""

from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=5,
        max_length=500,
        examples=["What was Apple's total revenue in 2024?"],
    )
    ticker: str | None = Field(
        default=None,
        pattern=r"^[A-Z]{1,5}(-[A-Z])?$",
        examples=["AAPL"],
    )
    section: Literal[
        "business",
        "risk_factors",
        "mdna",
        "financial_statements",
        "financial_table",
    ] | None = Field(default=None, examples=["financial_table"])
    top_k: int = Field(default=5, ge=1, le=10)
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Session ID for multi-turn conversation. If omitted, the request "
            "runs in stateless mode."
        ),
        examples=["test-session-001"],
    )
    answer_language: Literal["en", "vi"] = Field(
        default="en",
        description="Language for the generated answer; filing evidence remains verbatim.",
    )


class SourceChunk(BaseModel):
    citation: str
    score: float
    text_preview: str
    text: str | None = None
    chunk_id: str | None = None
    document_id: str | None = None
    ticker: str | None = None
    filing_type: str | None = None
    section: str | None = None
    filing_date: str | None = None
    report_date: str | None = None
    chunk_index: int | None = None
    source_url: str | None = None
    rank: int | None = None
    score_kind: Literal["retrieval", "cross_encoder", "rrf", "unknown"] | None = None
    reranker_score: float | None = None


class QueryInterpretation(BaseModel):
    """Safe, user-visible explanation of the retrieval query transformation."""

    original_question: str
    retrieval_question: str
    translation_method: str
    detected_ticker: str | None = None
    requested_periods: list[str] = Field(default_factory=list)
    is_comparative: bool = False


class QueryResponse(BaseModel):
    answer: str
    model_used: str
    sources: list[SourceChunk]
    num_chunks_retrieved: int
    answer_language: Literal["en", "vi"] = "en"
    query_interpretation: QueryInterpretation | None = None
    visual_answer: dict | None = None


class SubQueryInfo(BaseModel):
    query: str
    ticker: str | None
    section: str | None
    num_chunks: int


class DecomposedQueryResponse(BaseModel):
    answer: str
    model_used: str
    was_decomposed: bool
    sub_queries: list[SubQueryInfo]
    sources: list[SourceChunk]
    num_total_chunks: int
    answer_language: Literal["en", "vi"] = "en"
    query_interpretation: QueryInterpretation | None = None


class CacheTestRequest(BaseModel):
    query_a: str = Field(min_length=5)
    query_b: str = Field(min_length=5)


class RetrievalInspectRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    ticker: str | None = Field(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$")
    section: Literal[
        "business",
        "risk_factors",
        "mdna",
        "financial_statements",
        "financial_table",
    ] | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    candidate_pool: int = Field(default=10, ge=10, le=50)
    preset: Literal["bm25", "dense", "hybrid", "hybrid_rerank"] = "hybrid_rerank"


# --- API-003 catalog facets and statistics ---------------------------------


class CatalogScope(BaseModel):
    """The exact filters a catalog response was computed under."""

    ticker: str | None = None
    section: str | None = None
    year: int | None = None
    filing_date: str | None = None
    search: str | None = None
    documents: int = Field(ge=0)


class CatalogFacetValue(BaseModel):
    """One recorded facet value with its truthful document count."""

    value: str | int
    count: int = Field(ge=0)


class CatalogFacet(BaseModel):
    """One facet dimension and its recorded values.

    ``availability`` distinguishes a recorded dimension from one the stored
    metadata never carries; an unknown dimension carries a reason and must not
    be read as a real zero.
    """

    dimension: Literal["company", "year", "section"]
    availability: Literal["recorded", "unknown"]
    reason: str | None = None
    documents_without_value: int | None = Field(default=None, ge=0)
    values: list[CatalogFacetValue]


class DocumentFacetsResponse(BaseModel):
    """Public, provider-free catalog facets for the applied scope."""

    generated_at: str
    count_basis: Literal["all_filters_except_own_dimension"]
    scope: CatalogScope
    facets: list[CatalogFacet]


class CatalogDateDimension(BaseModel):
    """Availability of one catalog date dimension."""

    availability: Literal["recorded", "unknown"]
    reason: str | None = None


class CatalogFilingDates(CatalogDateDimension):
    """Filing-date coverage with the recorded year range."""

    earliest: int | None = None
    latest: int | None = None
    documents_without_value: int = Field(ge=0)


class CatalogReportDates(CatalogDateDimension):
    """Report-date coverage as recorded by the loaded documents."""

    documents_with_value: int = Field(ge=0)


class CatalogSections(BaseModel):
    """Section coverage in canonical corpus order."""

    availability: Literal["recorded", "unknown"]
    reason: str | None = None
    documents_without_value: int = Field(ge=0)
    values: list[CatalogFacetValue]


class CatalogFilingType(BaseModel):
    """Filing-type availability; unknown while no artifact records one."""

    availability: Literal["recorded", "unknown"]
    reason: str | None = None
    value: str | None = None


class DocumentStatsResponse(BaseModel):
    """Public, provider-free catalog totals and per-dimension availability."""

    generated_at: str
    documents: int = Field(ge=0)
    companies: int = Field(ge=0)
    chunks: int = Field(ge=0)
    configured_companies: int = Field(ge=0)
    configured_companies_without_documents: list[str]
    configured_companies_with_documents: list[str]
    filing_dates: CatalogFilingDates
    report_dates: CatalogReportDates
    sections: CatalogSections
    filing_type: CatalogFilingType
