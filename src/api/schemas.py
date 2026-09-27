"""Stable request and response models for the existing HTTP API."""

from typing import Any, Literal

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
    # API-005 document/date filters. The document id is an opaque token, never
    # a filesystem path; the date and year follow the catalog's own scope.
    document_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )
    filing_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    year: int | None = Field(default=None, ge=1900, le=2200)
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


# --- API-004 discovery search ----------------------------------------------


class SearchRequest(BaseModel):
    """One provider-free keyword discovery request."""

    query: str = Field(
        min_length=2,
        max_length=200,
        examples=["Apple revenue 2024"],
    )
    mode: Literal["keyword"] = "keyword"
    group_by: Literal["document", "chunk"] = "document"
    ticker: str | None = Field(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$")
    section: str | None = Field(default=None, max_length=64)
    year: int | None = Field(default=None, ge=1900, le=2200)
    filing_date: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class DiscoverySnippet(BaseModel):
    """Real-text excerpt with half-open Unicode code-point match ranges."""

    text: str
    ranges: list[tuple[int, int]]
    truncated: bool


class DiscoveryHit(BaseModel):
    """One ranked chunk hit with its canonical identity preserved."""

    chunk_id: str
    document_id: str
    ticker: str | None = None
    section: str | None = None
    filing_date: str | None = None
    report_date: str | None = None
    chunk_index: int | None = None
    score: float
    snippet: DiscoverySnippet


class DiscoveryGroup(BaseModel):
    """One grouped result (a filing) with its best-matching hits."""

    document_id: str
    ticker: str | None = None
    filing_date: str | None = None
    report_date: str | None = None
    sections: list[str]
    best_score: float
    hit_count: int = Field(ge=0)
    hits: list[DiscoveryHit]


class DiscoveryQuery(BaseModel):
    """The submitted query and the deterministic form actually searched."""

    text: str
    normalized: str
    mode: Literal["keyword"]


class DiscoveryGrouping(BaseModel):
    """Grouping applied to the snapshot."""

    group_by: Literal["document", "chunk"]
    group_count: int = Field(ge=0)
    hit_count: int = Field(ge=0)


class DiscoveryEngine(BaseModel):
    """The ranking engine identity and its explicit definition."""

    key: str
    version: str
    definition: str


class DiscoveryScopeMetadata(BaseModel):
    """Scope and truthful count metadata for a snapshot.

    ``count_scope`` states that the reported total is bounded by the candidate
    ceiling, so a client can never present it as a whole-corpus total.
    """

    ticker: str | None = None
    section: str | None = None
    year: int | None = None
    filing_date: str | None = None
    documents: int = Field(ge=0)
    count_scope: Literal["bounded_candidates", "no_matches"]
    candidate_ceiling: int = Field(ge=1)
    limited_by_ceiling: bool
    matched_documents: int = Field(ge=0)
    matched_chunks: int = Field(ge=0)


class DiscoverySnapshotResponse(BaseModel):
    """A discovery snapshot page: a stable ranked result set plus its scope."""

    search_id: str
    query: DiscoveryQuery
    grouping: DiscoveryGrouping
    engine: DiscoveryEngine
    scope: DiscoveryScopeMetadata
    items: list[DiscoveryGroup] | list[DiscoveryHit]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    facets: list[CatalogFacet]
    created_at: str
    expires_at: str
    ttl_seconds: int = Field(ge=0)


# --- DATA-003 typed collections --------------------------------------------
# Request bodies only: responses are the repository's own typed payloads, so one
# shape serves the routes, the repository and the per-collection export.


class CollectionCreateRequest(BaseModel):
    """Create one collection; the caller may name its opaque identity."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2_000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    favorite: bool = False
    private: bool = True
    collection_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )


class CollectionUpdateRequest(BaseModel):
    """Update mutable fields with a revision precondition."""

    revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    tags: list[str] | None = Field(default=None, max_length=20)
    favorite: bool | None = None
    private: bool | None = None


class CollectionItemRequest(BaseModel):
    """Add one typed member; membership is validated by the domain, by kind."""

    item_kind: str = Field(min_length=1, max_length=32)
    citation: str = Field(default="", max_length=500)
    excerpt: str = Field(default="", max_length=10_000)
    reference: dict[str, Any] | None = None
    snapshot: dict[str, Any] | None = None
    item_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )


class CollectionNoteRequest(BaseModel):
    """Add a note, bound to an evidence reference when one is supplied."""

    text: str = Field(min_length=1, max_length=10_000)
    evidence_ref: dict[str, Any] | None = None
    note_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )


class CollectionNoteUpdateRequest(BaseModel):
    """Edit a note's text with a revision precondition."""

    revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=10_000)
