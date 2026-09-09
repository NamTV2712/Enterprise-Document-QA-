"""
Module: app.py
FastAPI application for RAG pipeline.
Design: Load all heavy objects (model, DB connection) at once
at startup via the lifespan context manager.
"""

import logging
import os
import re
import time
import asyncio
import functools
import inspect
import threading
import unicodedata
import uuid
from contextlib import asynccontextmanager
from typing import Any, Callable, Literal, TypeVar

import anyio.to_thread
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from configs.settings import settings
from configs.logging_config import setup_logging
from configs.tickers import TICKERS
from src.generation.generator import Generator
from src.generation.query_decomposer import QueryCancelled, QueryDecomposer
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_normalizer import normalize_retrieval_question
from src.retrieval.vector_store import VectorStore
from src.api.telemetry import RequestTelemetry
from src.api.proxy import get_rate_limit_key
from src.evaluation.public_report import get_public_report, list_public_reports

import json as json_lib
from fastapi.responses import JSONResponse, StreamingResponse

# Setup structured logging (use json_mode=True in production)
setup_logging(level="INFO", json_mode=False)
logger = logging.getLogger(__name__)

# Global dictionary for pipeline storage — populated at startup, used in endpoints.
_state: dict[str, Any] = {}
SUPPORTED_SECTIONS = [
    "business",
    "risk_factors",
    "mdna",
    "financial_statements",
    "financial_table",
]
INTERNAL_ERROR_DETAIL = (
    "An internal error occurred while processing your question. Please try again."
)
QUERY_TIMEOUT_DETAIL = "The query timed out. Please try again."
QUERY_TIMEOUT_SECONDS = 60.0
DECOMPOSED_TIMEOUT_DETAIL = "The comparative query timed out. Please try again."
DECOMPOSED_TIMEOUT_SECONDS = 120.0
STREAM_TIMEOUT_DETAIL = "The query timed out. Please try again."
STREAM_QUERY_TIMEOUT_SECONDS = 60.0
STREAM_QUEUE_POLL_SECONDS = 0.25
T = TypeVar("T")
limiter = Limiter(key_func=get_rate_limit_key)
telemetry = RequestTelemetry()


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a machine-readable client rate-limit response distinct from provider quota."""
    retry_after_seconds = 60
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after_seconds)},
        content={
            "error": "Rate limit exceeded. Please retry later.",
            "code": "client_rate_limited",
            "retry_after_seconds": retry_after_seconds,
        },
    )


def _provider_failure_detail(error: Exception) -> tuple[int, dict[str, Any]] | None:
    """Map provider transport failures to safe structured HTTP details."""
    status_code = getattr(error, "status_code", None)
    error_name = type(error).__name__.lower()
    message = str(error).lower()
    is_quota = status_code == 429 or "rate limit" in message or "quota" in message
    if is_quota:
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", None) or {}
        retry_after = headers.get("retry-after") if hasattr(headers, "get") else None
        if retry_after is None:
            match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)\s*(ms|s)", message)
            if match:
                retry_after = float(match.group(1)) / 1000 if match.group(2) == "ms" else float(match.group(1))
        try:
            retry_after_seconds = max(1, int(float(retry_after))) if retry_after is not None else 60
        except (TypeError, ValueError):
            retry_after_seconds = 60
        return 429, {
            "code": "provider_quota",
            "message": "The provider quota is temporarily unavailable. Please retry later.",
            "retry_after_seconds": retry_after_seconds,
        }
    if status_code in {408, 500, 502, 503, 504} or "timeout" in error_name or "connection" in error_name:
        return 503, {
            "code": "provider_unavailable",
            "message": "The provider is temporarily unavailable. Please retry later.",
        }
    return None


def _load_supported_tickers() -> list[str]:
    cached_tickers = _state.get("supported_tickers")
    if cached_tickers is not None:
        return list(cached_tickers)

    tickers = []
    for ticker in TICKERS:
        ticker_dir = settings.data_processed_dir / ticker
        if any(path.stat().st_size > 0 for path in ticker_dir.glob("*_chunks_embedded.jsonl")):
            tickers.append(ticker)
    return tickers or TICKERS


def _loaded_retrieval_chunks() -> list[dict[str, Any]]:
    pipeline: RAGPipeline | None = _state.get("pipeline")
    retriever = getattr(pipeline, "retriever", None)
    chunks = getattr(retriever, "_all_chunks", None)
    return chunks if isinstance(chunks, list) else []


def _document_id(chunk: dict[str, Any]) -> str:
    accession = chunk.get("accession_number")
    if isinstance(accession, str) and accession:
        return f"{chunk.get('ticker', 'UNKNOWN')}:{accession}"
    return f"{chunk.get('ticker', 'UNKNOWN')}:{chunk.get('filing_date', 'unknown')}"


def _document_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        document_id = _document_id(chunk)
        row = grouped.setdefault(
            document_id,
            {
                "document_id": document_id,
                "ticker": chunk.get("ticker"),
                "filing_date": chunk.get("filing_date"),
                "accession_number": chunk.get("accession_number"),
                "sections": set(),
                "chunk_count": 0,
                "source_url": chunk.get("source_url") or chunk.get("filing_url"),
            },
        )
        if chunk.get("section"):
            row["sections"].add(chunk["section"])
        row["chunk_count"] += 1
    return [
        {**row, "sections": sorted(row["sections"])}
        for row in sorted(
            grouped.values(),
            key=lambda item: (
                item["ticker"] or "",
                item["filing_date"] or "",
                item["document_id"],
            ),
        )
    ]


def _chunk_sort_key(chunk: dict[str, Any]) -> tuple[Any, ...]:
    section = str(chunk.get("section") or "")
    try:
        section_order = SUPPORTED_SECTIONS.index(section)
    except ValueError:
        section_order = len(SUPPORTED_SECTIONS)
    chunk_index = chunk.get("chunk_index")
    has_index = isinstance(chunk_index, int) and chunk_index >= 0
    return (
        section_order,
        section,
        0 if has_index else 1,
        chunk_index if has_index else 0,
        str(chunk.get("chunk_id") or ""),
        str(chunk.get("text") or ""),
    )


def _build_document_chunk_indexes(
    chunks: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[tuple[str, dict[str, Any]]]]]:
    """Build stable document lists and a direct chunk lookup map.

    Missing chunk IDs remain visible in document lists but cannot be addressed
    by the direct detail route. Duplicate IDs are retained in the lookup so
    the detail route can return an explicit ambiguity error instead of
    silently opening one arbitrary chunk.
    """
    chunks_by_document: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        chunks_by_document.setdefault(_document_id(chunk), []).append(chunk)
    for document_id, document_chunks in chunks_by_document.items():
        chunks_by_document[document_id] = sorted(document_chunks, key=_chunk_sort_key)

    chunks_by_id: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for document_id in sorted(chunks_by_document):
        for chunk in chunks_by_document[document_id]:
            chunk_id = chunk.get("chunk_id")
            if isinstance(chunk_id, str) and chunk_id:
                chunks_by_id.setdefault(chunk_id, []).append((document_id, chunk))
    return chunks_by_document, chunks_by_id


def _document_catalog() -> list[dict[str, Any]]:
    """Return the startup-built document metadata index when available."""
    cached = _state.get("document_rows")
    if isinstance(cached, list):
        return cached
    rows = _document_rows(_loaded_retrieval_chunks())
    _state["document_rows"] = rows
    return rows


def _document_chunks_index() -> dict[str, list[dict[str, Any]]]:
    """Return the startup-built document-to-chunks index, with test fallback."""
    cached = _state.get("document_chunks_by_id")
    if isinstance(cached, dict):
        return cached
    index, chunks_by_id = _build_document_chunk_indexes(_loaded_retrieval_chunks())
    _state["document_chunks_by_id"] = index
    _state["chunk_records_by_id"] = chunks_by_id
    return index


def _chunk_records_index() -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Return direct chunk lookup records, preserving duplicate ambiguity."""
    cached = _state.get("chunk_records_by_id")
    if isinstance(cached, dict):
        return cached
    _document_chunks_index()
    return _state.get("chunk_records_by_id", {})


def _embed_query_pair(
    pipeline: RAGPipeline,
    query_a: str,
    query_b: str,
) -> tuple[list[float], list[float]]:
    """Embed both queries in one worker because the shared model lock serializes them."""
    embed = getattr(pipeline.retriever, "embed_query", None)
    if embed is None:
        embed = pipeline.retriever.embedder.embed_query
    return embed(query_a), embed(query_b)


async def _run_query_with_timeout(
    func: Callable[..., T],
    timeout: float | None = None,
    **kwargs: Any,
) -> T:
    effective_timeout = timeout if timeout is not None else QUERY_TIMEOUT_SECONDS
    worker = anyio.to_thread.run_sync(
        functools.partial(func, **kwargs),
        abandon_on_cancel=True,
    )
    return await asyncio.wait_for(worker, timeout=effective_timeout)


def _get_pipeline() -> RAGPipeline:
    """Return the shared pipeline or raise 503 when startup has not finished."""
    pipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    return pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing hybrid RAG pipeline...")
    t0 = time.time()

    store = VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    )
    all_chunks = load_retrieval_chunks(store, settings.data_processed_dir)
    if not all_chunks:
        store.close()
        raise RuntimeError("No searchable chunks are available for retrieval")
    logger.info("Loaded %d chunks for BM25 index", len(all_chunks))

    embedder = Embedder(
        model_name=settings.embedding_model_id,
        revision=settings.embedding_model_revision or None,
    )
    retriever = HybridRetriever(
        embedder=embedder,
        store=store,
        all_chunks=all_chunks,
        cross_encoder_model=settings.reranker_model_id,
        cross_encoder_revision=settings.reranker_model_revision or None,
    )
    generator = Generator()
    pipeline = RAGPipeline(retriever=retriever, generator=generator)
    _state["pipeline"] = pipeline
    _state["decomposer"] = QueryDecomposer(pipeline=pipeline)
    _state["store"] = store
    _state["document_rows"] = _document_rows(all_chunks)
    chunks_by_document, chunks_by_id = _build_document_chunk_indexes(all_chunks)
    _state["document_chunks_by_id"] = chunks_by_document
    _state["chunk_records_by_id"] = chunks_by_id
    searchable_tickers = {chunk["ticker"] for chunk in all_chunks}
    _state["corpus"] = {
        "searchable_company_count": len(searchable_tickers),
        "indexed_chunk_count": len(all_chunks),
    }
    _state["supported_tickers"] = [
        ticker for ticker in TICKERS if ticker in searchable_tickers
    ]

    logger.info("Hybrid pipeline and decomposer ready after %.1f seconds", time.time() - t0)
    yield
    store.close()
    logger.info("VectorStore closed.")


app = FastAPI(
    title="Enterprise Document QA - SEC Filings RAG",
    description="The RAG system answers questions about SEC 10-K financial reporting",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "ngrok-skip-browser-warning"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def record_request_telemetry(request: Request, call_next: Callable) -> Any:
    """Log request lifecycle metadata without recording question or session content."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - started_at
        telemetry.record(request.url.path, 500, elapsed)
        logger.exception(
            "request_failed request_id=%s route=%s elapsed_ms=%.2f",
            request_id,
            request.url.path,
            elapsed * 1000,
        )
        raise
    elapsed = time.perf_counter() - started_at
    telemetry.record(request.url.path, response.status_code, elapsed)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete request_id=%s route=%s status=%d elapsed_ms=%.2f",
        request_id,
        request.url.path,
        response.status_code,
        elapsed * 1000,
    )
    return response


# --- Pydantic models for request/response ---

class QueryRequest(BaseModel):
    question: str = Field(
        min_length=5, max_length=500,
        examples=["What was Apple's total revenue in 2024?"]
    )
    ticker: str | None = Field(
        default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$",
        examples=["AAPL"]
    )
    section: Literal[
        "business",
        "risk_factors",
        "mdna",
        "financial_statements",
        "financial_table",
    ] | None = Field(
        default=None,
        examples=["financial_table"]
    )
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
    text_preview: str  # First 200 characters for collapsed evidence previews.
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


# --- Endpoints ---

def _health_payload() -> dict:
    pipeline: RAGPipeline | None = _state.get("pipeline")
    memory = getattr(pipeline, "memory", None)
    payload = {
        "status": "ok",
        "pipeline_ready": pipeline is not None,
        "memory": memory.get_stats() if memory else {},
    }
    if _state.get("corpus") is not None:
        payload["corpus"] = dict(_state["corpus"])
    # Optional release metadata: set by the Docker build/runtime. Only the
    # git revision and build version are exposed — never paths, internal
    # configuration, or secrets. Older frontends ignore unknown fields.
    build: dict[str, str] = {}
    if os.environ.get("GIT_REVISION"):
        build["revision"] = os.environ["GIT_REVISION"]
    if os.environ.get("BUILD_VERSION"):
        build["version"] = os.environ["BUILD_VERSION"]
    if build:
        payload["build"] = build
    return payload


def _source_chunk_payload(chunk: Any, rank: int | None = None) -> SourceChunk:
    """Serialize one retrieved chunk consistently across all query routes."""
    return SourceChunk(
        citation=chunk.citation,
        score=round(chunk.score, 4),
        text_preview=chunk.text[:200],
        text=chunk.text,
        chunk_id=chunk.chunk_id,
        document_id=getattr(chunk, "document_id", None),
        ticker=chunk.ticker,
        filing_type=getattr(chunk, "filing_type", None),
        section=chunk.section,
        filing_date=chunk.filing_date,
        report_date=getattr(chunk, "report_date", None),
        chunk_index=getattr(chunk, "chunk_index", None),
        source_url=getattr(chunk, "source_url", None),
        rank=rank,
        score_kind=getattr(chunk, "score_kind", None),
        reranker_score=getattr(chunk, "reranker_score", None),
    )


def _query_interpretation(original_question: str, normalized: Any) -> QueryInterpretation:
    """Serialize normalization metadata without exposing internal paths/config."""
    return QueryInterpretation(
        original_question=original_question,
        retrieval_question=normalized.question,
        translation_method=normalized.translation_method,
        detected_ticker=normalized.detected_ticker,
        requested_periods=list(normalized.requested_periods),
        is_comparative=normalized.is_comparative,
    )


@app.get("/health/live")
async def health_live() -> dict:
    """Report whether the API process can serve HTTP requests."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict:
    """Report whether the RAG pipeline is ready to accept query traffic."""
    payload = _health_payload()
    if not payload["pipeline_ready"]:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    return payload


@app.get("/health")
async def health() -> dict:
    """Return the legacy health payload used by the current frontend."""
    return _health_payload()


@app.post("/query", response_model=QueryResponse)
@limiter.shared_limit(settings.llm_rate_limit_burst, scope="llm-query-burst")
@limiter.shared_limit(settings.llm_rate_limit_daily, scope="llm-query-daily")
async def query(request: Request, body: QueryRequest) -> QueryResponse:
    """Main endpoint: receive the question, return the answer + source citation"""
    pipeline = _get_pipeline()

    if _contains_injection_pattern(body.question):
        logger.warning("Potential injection attempt blocked: %s", body.question[:50])
        raise HTTPException(
            status_code=400,
            detail="Your question contains patterns that cannot be processed. Please rephrase.",
        )

    original_question = _sanitize_question(body.question)
    normalized = normalize_retrieval_question(original_question)
    ticker = body.ticker or normalized.detected_ticker
    try:
        response = await _run_query_with_timeout(
            pipeline.query,
            question=normalized.question,
            top_k=body.top_k,
            ticker=ticker,
            section=body.section,
            session_id=body.session_id,
            answer_language=body.answer_language,
        )
        telemetry.record_provider_event("completed")
    except TimeoutError:
        logger.warning("Query timed out after %.1f seconds", QUERY_TIMEOUT_SECONDS)
        raise HTTPException(status_code=504, detail=QUERY_TIMEOUT_DETAIL)
    except Exception as e:
        provider_failure = _provider_failure_detail(e)
        if provider_failure is not None:
            status_code, detail = provider_failure
            telemetry.record_provider_event(
                "quota" if detail["code"] == "provider_quota" else "transport_error"
            )
            raise HTTPException(status_code=status_code, detail=detail) from e
        logger.exception("Error occurred while processing query: %s", e)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    sources = [
        _source_chunk_payload(chunk, rank=index + 1)
        for index, chunk in enumerate(response.retrieved_chunks)
    ]

    return QueryResponse(
        answer=response.answer,
        model_used=response.model_used,
        sources=sources,
        num_chunks_retrieved=len(response.retrieved_chunks),
        answer_language=response.answer_language,
        query_interpretation=_query_interpretation(original_question, normalized),
        visual_answer=response.visual_answer,
    )


@app.post("/query/decomposed", response_model=DecomposedQueryResponse)
@limiter.shared_limit(settings.llm_rate_limit_burst, scope="llm-query-burst")
@limiter.shared_limit(settings.llm_rate_limit_daily, scope="llm-query-daily")
@limiter.limit(settings.decomposed_rate_limit)
async def query_decomposed(
    request: Request,
    body: QueryRequest,
) -> DecomposedQueryResponse:
    """Handle complex or comparative questions with optional query decomposition.

    Simple questions fall back to the normal RAG pipeline. Complex questions are
    planned into focused sub-queries, retrieved independently, and synthesized
    into one grounded answer.
    """
    decomposer: QueryDecomposer | None = _state.get("decomposer")
    if decomposer is None:
        raise HTTPException(status_code=503, detail="The decomposer is not ready yet")

    telemetry.record_decomposed_request()

    if _contains_injection_pattern(body.question):
        logger.warning("Potential injection attempt blocked: %s", body.question[:50])
        raise HTTPException(
            status_code=400,
            detail="Your question contains patterns that cannot be processed. Please rephrase.",
        )

    original_question = _sanitize_question(body.question)
    normalized = normalize_retrieval_question(original_question)
    ticker = body.ticker or normalized.detected_ticker
    try:
        result = await _run_query_with_timeout(
            decomposer.run,
            timeout=DECOMPOSED_TIMEOUT_SECONDS,
            question=normalized.question,
            top_k=body.top_k,
            ticker=ticker,
            section=body.section,
            session_id=body.session_id,
            answer_language=body.answer_language,
        )
        telemetry.record_provider_event("completed")
    except TimeoutError:
        logger.warning(
            "Decomposed query timed out after %.1f seconds",
            DECOMPOSED_TIMEOUT_SECONDS,
        )
        raise HTTPException(status_code=504, detail=DECOMPOSED_TIMEOUT_DETAIL)
    except Exception as e:
        provider_failure = _provider_failure_detail(e)
        if provider_failure is not None:
            status_code, detail = provider_failure
            telemetry.record_provider_event(
                "quota" if detail["code"] == "provider_quota" else "transport_error"
            )
            raise HTTPException(status_code=status_code, detail=detail) from e
        logger.exception("Error occurred while processing decomposed query: %s", e)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    return DecomposedQueryResponse(
        answer=result.answer,
        model_used=result.model_used,
        was_decomposed=result.was_decomposed,
        sub_queries=[
            SubQueryInfo(
                query=sub_query.query,
                ticker=sub_query.ticker,
                section=sub_query.section,
                num_chunks=len(sub_query.retrieved_chunks),
            )
            for sub_query in result.sub_queries
        ],
        sources=[
            _source_chunk_payload(chunk, rank=index + 1)
            for index, chunk in enumerate(result.all_chunks[:10])
        ],
        num_total_chunks=len(result.all_chunks),
        answer_language=body.answer_language,
        query_interpretation=_query_interpretation(original_question, normalized),
    )


@app.post("/query/decomposed/stream")
@limiter.shared_limit(settings.llm_rate_limit_burst, scope="llm-query-burst")
@limiter.shared_limit(settings.llm_rate_limit_daily, scope="llm-query-daily")
@limiter.limit(settings.decomposed_rate_limit)
async def query_decomposed_stream(request: Request, request_body: QueryRequest):
    """Stream comparative/decomposed work without removing the JSON endpoint."""
    decomposer: QueryDecomposer | None = _state.get("decomposer")
    if decomposer is None:
        raise HTTPException(status_code=503, detail="The decomposer is not ready yet")
    if _contains_injection_pattern(request_body.question):
        logger.warning("Potential injection attempt blocked: %s", request_body.question[:50])
        raise HTTPException(
            status_code=400,
            detail="Your question contains patterns that cannot be processed. Please rephrase.",
        )

    telemetry.record_decomposed_request()
    request_body.question = _sanitize_question(request_body.question)
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    async def event_generator():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue(maxsize=128)
        cancel_event = threading.Event()
        sequence_lock = threading.Lock()
        sequence = 0

        def enqueue(event: tuple[str, Any] | None) -> None:
            if cancel_event.is_set() and event is not None:
                return

            def put_event() -> None:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    cancel_event.set()

            try:
                loop.call_soon_threadsafe(put_event)
            except RuntimeError:
                cancel_event.set()

        def stage_callback(
            stage_id: str,
            status: str,
            elapsed_ms: float | None,
            counters: dict[str, Any] | None,
            metadata: dict[str, Any] | None,
        ) -> None:
            nonlocal sequence
            with sequence_lock:
                sequence += 1
                event = {
                    "version": 1,
                    "request_id": request_id,
                    "sequence": sequence,
                    "stage_id": stage_id,
                    "status": status,
                }
            if elapsed_ms is not None:
                event["elapsed_ms"] = round(elapsed_ms, 3)
            if counters:
                event["counters"] = counters
            if metadata:
                event["metadata"] = metadata
            enqueue(("stage", event))

        def run_stream() -> None:
            normalized = normalize_retrieval_question(request_body.question)
            ticker = request_body.ticker or normalized.detected_ticker
            try:
                result = decomposer.run(
                    question=normalized.question,
                    top_k=request_body.top_k,
                    ticker=ticker,
                    section=request_body.section,
                    session_id=request_body.session_id,
                    answer_language=request_body.answer_language,
                    stage_callback=stage_callback,
                    cancel_event=cancel_event,
                )
                if cancel_event.is_set():
                    return
                sources = [
                    _source_chunk_payload(chunk, rank=index + 1).model_dump()
                    for index, chunk in enumerate(result.all_chunks[:10])
                ]
                enqueue(("sources", sources))
                answer = result.answer
                for start in range(0, len(answer), 160):
                    if cancel_event.is_set():
                        return
                    enqueue(("token", answer[start : start + 160]))
                enqueue((
                    "done",
                    {
                        "request_id": request_id,
                        "request_status": "completed",
                        "model_used": result.model_used,
                        "was_decomposed": result.was_decomposed,
                        "sub_queries": [
                            {
                                "query": sub_query.query,
                                "ticker": sub_query.ticker,
                                "section": sub_query.section,
                                "num_chunks": len(sub_query.retrieved_chunks),
                            }
                            for sub_query in result.sub_queries
                        ],
                        "num_total_chunks": len(result.all_chunks),
                        "query_interpretation": _query_interpretation(
                            request_body.question, normalized
                        ).model_dump(),
                    },
                ))
                telemetry.record_provider_event("completed")
            except QueryCancelled:
                logger.info("Comparative stream cancelled by client")
            except Exception as error:
                provider_failure = _provider_failure_detail(error)
                if provider_failure is not None:
                    telemetry.record_provider_event(
                        "quota" if provider_failure[1]["code"] == "provider_quota" else "transport_error"
                    )
                else:
                    logger.exception("Unhandled comparative streaming endpoint error")
                if not cancel_event.is_set():
                    enqueue(("error", provider_failure[1] if provider_failure else INTERNAL_ERROR_DETAIL))
            finally:
                enqueue(None)

        threading.Thread(target=run_stream, daemon=True).start()
        started_at = time.monotonic()
        while True:
            if await request.is_disconnected():
                cancel_event.set()
                logger.info("Comparative streaming client disconnected; cancelling query")
                break
            elapsed = time.monotonic() - started_at
            if elapsed >= DECOMPOSED_TIMEOUT_SECONDS:
                cancel_event.set()
                yield f"data: {json_lib.dumps({'type': 'error', 'data': DECOMPOSED_TIMEOUT_DETAIL})}\n\n"
                break
            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=min(STREAM_QUEUE_POLL_SECONDS, DECOMPOSED_TIMEOUT_SECONDS - elapsed),
                )
            except asyncio.TimeoutError:
                continue
            if event is None:
                break
            event_type, data = event
            payload = json_lib.dumps({"type": event_type, "data": data}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            if event_type in {"done", "error"}:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/supported-tickers")
async def supported_tickers() -> dict:
    """List of supported tickers — helps the UI/user know what they can ask about."""
    tickers = await run_in_threadpool(_load_supported_tickers)
    return {
        "tickers": tickers,
        "sections": SUPPORTED_SECTIONS,
    }


@app.get("/documents")
async def documents(
    ticker: str | None = Query(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$"),
    section: str | None = Query(default=None),
    filing_date: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict:
    """Return a paginated catalog derived from loaded retrieval metadata."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    rows = _document_catalog()
    search_folded = search.casefold().strip() if search else ""
    filtered = [
        row
        for row in rows
        if (ticker is None or row["ticker"] == ticker)
        and (filing_date is None or row["filing_date"] == filing_date)
        and (section is None or section in row["sections"])
        and (
            not search_folded
            or search_folded in " ".join(
                str(row.get(field) or "")
                for field in ("document_id", "ticker", "filing_date", "accession_number")
            ).casefold()
        )
    ]
    start = (page - 1) * page_size
    return {
        "items": filtered[start : start + page_size],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
    }


@app.get("/documents/{document_id}")
async def document_detail(document_id: str) -> dict:
    """Return one public document record without exposing filesystem paths."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    rows = _document_catalog()
    row = next((item for item in rows if item["document_id"] == document_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return row


@app.get("/documents/{document_id}/chunks")
async def document_chunks(
    document_id: str,
    section: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict:
    """Return paginated source previews for one document."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    search_folded = search.casefold().strip() if search else ""
    matching = [
        chunk
        for chunk in _document_chunks_index().get(document_id, [])
        if _document_id(chunk) == document_id
        and (section is None or chunk.get("section") == section)
        and (not search_folded or search_folded in str(chunk.get("text") or "").casefold())
    ]
    start = (page - 1) * page_size
    items = []
    for chunk in matching[start : start + page_size]:
        items.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "ticker": chunk.get("ticker"),
                "section": chunk.get("section"),
                "filing_date": chunk.get("filing_date"),
                "report_date": chunk.get("report_date"),
                "accession_number": chunk.get("accession_number"),
                "chunk_index": chunk.get("chunk_index"),
                "text_preview": str(chunk.get("text") or "")[:500],
                "text_length": len(str(chunk.get("text") or "")),
                "source_url": chunk.get("source_url") or chunk.get("filing_url"),
            }
        )
    return {"items": items, "total": len(matching), "page": page, "page_size": page_size}


@app.get("/chunks/{chunk_id}")
async def chunk_detail(chunk_id: str) -> dict:
    """Return one full source excerpt for the evidence reader."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    records = _chunk_records_index().get(chunk_id, [])
    if not records:
        raise HTTPException(status_code=404, detail="Chunk not found")
    if len(records) > 1:
        raise HTTPException(status_code=409, detail="Chunk ID is ambiguous")
    document_id, chunk = records[0]
    text = str(chunk.get("text") or "")
    return {
        "chunk_id": chunk.get("chunk_id"),
        "document_id": document_id,
        "ticker": chunk.get("ticker"),
        "section": chunk.get("section"),
        "filing_date": chunk.get("filing_date"),
        "report_date": chunk.get("report_date"),
        "accession_number": chunk.get("accession_number"),
        "chunk_index": chunk.get("chunk_index"),
        "text": text,
        "text_preview": text[:500],
        "text_length": len(text),
        "source_url": chunk.get("source_url") or chunk.get("filing_url"),
    }


@app.get("/system/info")
async def system_info() -> dict:
    """Expose allowlisted build, model and corpus metadata for the workspace."""
    pipeline: RAGPipeline | None = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    retriever = pipeline.retriever
    return {
        "api_version": app.version,
        "corpus": dict(_state.get("corpus") or {}),
        "retrieval": {
            "embedding_model": getattr(getattr(retriever, "embedder", None), "model_name", None),
            "reranker_model": getattr(retriever, "cross_encoder_model", None),
            "presets": ["bm25", "dense", "hybrid", "hybrid_rerank"],
            "default": "hybrid_rerank",
        },
        "capabilities": {
            "stage_events": True,
            "comparative_stream": True,
            "document_indexed_viewer": True,
        },
        "build": {
            key: os.environ[key]
            for key in ("GIT_REVISION", "BUILD_VERSION")
            if os.environ.get(key)
        },
    }


@app.get("/evaluation/runs")
async def evaluation_runs(
    status: Literal["official", "candidate", "historical", "incomplete"] | None = None,
    language: Literal["en", "vi"] | None = None,
    intent: str | None = Query(default=None, max_length=80),
    ticker: str | None = Query(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$"),
    gate: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List validated, explicitly published evaluation summaries only."""
    reports = list_public_reports(root=settings.data_public_evaluations_dir)
    filtered: list[dict[str, Any]] = []
    for summary in reports:
        if status is not None and summary["status"] != status:
            continue
        if language is None and intent is None and ticker is None and gate is None:
            filtered.append(summary)
            continue
        detail = get_public_report(summary["run_id"], root=settings.data_public_evaluations_dir)
        if detail is None:
            continue
        cases = detail["cases"]
        if language is not None and not any(case["language"] == language for case in cases):
            continue
        if intent is not None and not any(case.get("intent") == intent for case in cases):
            continue
        if ticker is not None and not any(case.get("ticker") == ticker for case in cases):
            continue
        if gate is not None and not any(case.get("gates", {}).get(gate) is True for case in cases):
            continue
        filtered.append(summary)
    start = (page - 1) * page_size
    return {
        "items": filtered[start : start + page_size],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
    }


@app.get("/evaluation/runs/{run_id}")
async def evaluation_run(run_id: str) -> dict:
    """Return one validated public report; arbitrary filesystem paths are impossible."""
    report = get_public_report(run_id, root=settings.data_public_evaluations_dir)
    if report is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return report


@app.post("/retrieval/inspect")
@limiter.limit("10/minute")
async def retrieval_inspect(request: Request, body: RetrievalInspectRequest) -> dict:
    """Inspect local retrieval stages without invoking the language model."""
    pipeline: RAGPipeline | None = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    if _contains_injection_pattern(body.question):
        raise HTTPException(
            status_code=400,
            detail="Your question contains patterns that cannot be processed. Please rephrase.",
        )
    original_question = _sanitize_question(body.question)
    normalized = normalize_retrieval_question(original_question)
    ticker = body.ticker or normalized.detected_ticker
    try:
        trace = await run_in_threadpool(
            pipeline.retriever.inspect,
            query=normalized.question,
            top_k=body.top_k,
            ticker=ticker,
            section=body.section,
            candidate_pool=body.candidate_pool,
            preset=body.preset,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception("Retrieval inspection failed")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    return {
        "query_interpretation": _query_interpretation(original_question, normalized),
        "trace": trace,
    }


SESSION_ID_MAX_LENGTH = 100
SESSION_ID_PATTERN = re.compile(rf"[A-Za-z0-9_-]{{1,{SESSION_ID_MAX_LENGTH}}}")
INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "ignore all instructions",
    "disregard previous",
    "disregard all previous",
    "forget your instructions",
    "forget previous instructions",
    "you are now",
    "act as",
    "pretend to be",
    "new instructions:",
    "system prompt:",
]


def _contains_injection_pattern(text: str) -> bool:
    """Check if text contains common prompt injection patterns."""
    lower = text.lower()
    return any(pattern in lower for pattern in INJECTION_PATTERNS)


def _sanitize_question(text: str) -> str:
    """Strip control/format characters and normalize Unicode before LLM use.

    Removes Unicode category Cc (control) except tab/newline/carriage return
    and Cf (format, e.g. zero-width spaces, RTL overrides) so hidden
    characters cannot alter retrieval or prompt behavior.
    """
    cleaned = "".join(
        ch
        for ch in text
        if ch in "\t\n\r" or unicodedata.category(ch) not in ("Cc", "Cf")
    )
    return unicodedata.normalize("NFC", cleaned).strip()


def _validate_session_id(session_id: str) -> None:
    """Validate session ID charset and length to prevent routing/log abuse."""
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Session ID may only contain letters, digits, hyphens, "
                f"and underscores (max {SESSION_ID_MAX_LENGTH} characters)"
            ),
        )


@app.delete("/session/{session_id}")
async def clear_session(session_id: str) -> dict:
    """Clear one conversation session."""
    _validate_session_id(session_id)
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    pipeline.memory.clear_session(session_id)
    return {"cleared": session_id}


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str) -> dict:
    """Return conversation history for debugging and UI rendering.

    The optional ``context`` block reports backend session state without
    creating or refreshing the session: ``available`` with the TTL budget
    that remains, or ``missing`` when the session expired or never existed.
    """
    _validate_session_id(session_id)
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    snapshot = pipeline.memory.get_history_snapshot(session_id)
    return {
        "session_id": session_id,
        "turns": [
            {
                "user": turn.user_message,
                "assistant": turn.assistant_message,
                "rewritten_query": turn.rewritten_query,
            }
            for turn in snapshot.turns
        ],
        "context": {
            "status": snapshot.status,
            "retained_turns": snapshot.retained_turns,
            "ttl_remaining_seconds": snapshot.ttl_remaining_seconds,
        },
    }


@app.get("/cache/stats")
async def cache_stats() -> dict:
    """Return semantic cache metrics."""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    return pipeline.cache.get_stats()


@app.get("/metrics")
async def metrics() -> dict:
    """Expose aggregate request, error, and latency counters when enabled."""
    if not settings.enable_metrics_endpoint:
        raise HTTPException(status_code=403, detail="Metrics endpoint is disabled")
    return telemetry.snapshot()


@app.post("/cache/clear")
async def cache_clear() -> dict:
    """Clear semantic cache entries and reset cache metrics."""
    if not settings.enable_cache_clear:
        raise HTTPException(
            status_code=403,
            detail="Cache clearing is disabled on this deployment",
        )
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    count = pipeline.cache.clear()
    return {"cleared_entries": count}


@app.post("/cache/test")
@limiter.limit(settings.cache_test_rate_limit)
async def cache_test_similarity(request: Request, body: CacheTestRequest) -> dict:
    """Compare two query embeddings to tune the semantic cache threshold."""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    emb_a, emb_b = await run_in_threadpool(
        _embed_query_pair,
        pipeline,
        body.query_a,
        body.query_b,
    )
    similarity = pipeline.cache.test_similarity(emb_a, emb_b)
    return {
        "query_a": body.query_a,
        "query_b": body.query_b,
        "similarity": round(similarity, 6),
        "threshold": pipeline.cache.threshold,
        "would_cache_hit": similarity >= pipeline.cache.threshold,
    }

@app.post("/query/stream")
@limiter.shared_limit(settings.llm_rate_limit_burst, scope="llm-query-burst")
@limiter.shared_limit(settings.llm_rate_limit_daily, scope="llm-query-daily")
async def query_stream(request: Request, request_body: QueryRequest):
    """Streaming endpoint using Server-Sent Events (SSE).

    Each event is emitted as `data: {json}\n\n` per the SSE spec.
    """
    pipeline = _get_pipeline()

    telemetry.record_streaming_request()

    if _contains_injection_pattern(request_body.question):
        logger.warning(
            "Potential injection attempt blocked: %s", request_body.question[:50]
        )
        raise HTTPException(
            status_code=400,
            detail="Your question contains patterns that cannot be processed. Please rephrase.",
        )
    request_body.question = _sanitize_question(request_body.question)

    async def event_generator():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue(maxsize=128)
        cancel_event = threading.Event()

        def enqueue(event: tuple[str, Any] | None) -> None:
            if cancel_event.is_set() and event is not None:
                return

            def put_event() -> None:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    cancel_event.set()

            try:
                loop.call_soon_threadsafe(put_event)
            except RuntimeError:
                cancel_event.set()

        def run_stream() -> None:
            normalized = normalize_retrieval_question(request_body.question)
            ticker = request_body.ticker or normalized.detected_ticker
            try:
                stream_kwargs: dict[str, Any] = {
                    "question": normalized.question,
                    "top_k": request_body.top_k,
                    "ticker": ticker,
                    "section": request_body.section,
                    "session_id": request_body.session_id,
                    "cancel_event": cancel_event,
                    "answer_language": request_body.answer_language,
                }
                try:
                    stream_parameters = inspect.signature(pipeline.query_stream).parameters
                except (TypeError, ValueError):
                    stream_parameters = {}
                if "request_id" in stream_parameters or any(
                    parameter.kind is inspect.Parameter.VAR_KEYWORD
                    for parameter in stream_parameters.values()
                ):
                    stream_kwargs["request_id"] = getattr(request.state, "request_id", None) or str(uuid.uuid4())

                for event_type, data in pipeline.query_stream(**stream_kwargs):
                    if cancel_event.is_set():
                        break
                    safe_data = INTERNAL_ERROR_DETAIL if event_type == "error" else data
                    if event_type == "done":
                        safe_data = {
                            **(data if isinstance(data, dict) else {}),
                            "query_interpretation": _query_interpretation(
                                request_body.question, normalized
                            ).model_dump(),
                        }
                    enqueue((event_type, safe_data))
                    if event_type in {"done", "error"}:
                        break
            except Exception as e:
                logger.exception("Unhandled streaming endpoint error: %s", e)
                enqueue(("error", INTERNAL_ERROR_DETAIL))
            finally:
                enqueue(None)

        threading.Thread(target=run_stream, daemon=True).start()
        started_at = time.monotonic()

        try:
            while True:
                if await request.is_disconnected():
                    cancel_event.set()
                    logger.info("Streaming client disconnected; cancelling query")
                    break

                elapsed = time.monotonic() - started_at
                if elapsed >= STREAM_QUERY_TIMEOUT_SECONDS:
                    cancel_event.set()
                    timeout_payload = json_lib.dumps(
                        {"type": "error", "data": STREAM_TIMEOUT_DETAIL}
                    )
                    yield f"data: {timeout_payload}\n\n"
                    break

                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=min(
                            STREAM_QUEUE_POLL_SECONDS,
                            STREAM_QUERY_TIMEOUT_SECONDS - elapsed,
                        ),
                    )
                except asyncio.TimeoutError:
                    continue

                if event is None:
                    break
                event_type, data = event
                try:
                    payload = json_lib.dumps(
                        {"type": event_type, "data": data},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
                except Exception as e:
                    logger.exception("Failed to serialize streaming response event: %s", e)
                    error_payload = json_lib.dumps(
                        {"type": "error", "data": INTERNAL_ERROR_DETAIL}
                    )
                    yield f"data: {error_payload}\n\n"
                    break

                if event_type in {"done", "error"}:
                    break
        finally:
            cancel_event.set()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering if deploying after reverse proxy
        },
    )
