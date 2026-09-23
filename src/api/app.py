"""
Module: app.py
FastAPI application for RAG pipeline.
Design: Load all heavy objects (model, DB connection) at once
at startup via the lifespan context manager.
"""

import logging
import hashlib
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

from pathlib import Path

import anyio.to_thread
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
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
from src.api.content_presentation import build_chunk_presentation
from src.api.catalog import (
    SUPPORTED_SECTIONS as catalog_sections,
    DEFAULT_SORT,
    SORT_FIELDS,
    filing_year,
    filter_documents,
    sort_documents,
)
from src.api.original_location import locate_chunk, whitespace_literal_matches
from src.api.original_viewer import OriginalViewerError, original_viewer, sec_index_url_for_document
from src.api.sec_urls import sanitize_sec_browser_url
from src.api.pdf_generator import PdfGenerationBusy, PdfGenerationError, generate_derived_pdf
from src.api.pdf_representation import (
    PdfArtifactIdentity,
    PdfEvidenceLocation,
    PdfMappingManifest,
    PdfRepresentationManifest,
    PdfStore,
    source_content_hash,
)
from src.api.document_reader_models import EvidenceLocation, ReaderManifest
from src.api.document_sources import build_reader_manifest
from src.api.structured_document import (
    StructuredContentResponse,
    StructuredDocumentService,
    StructuredOutlineResponse,
    StructuredSearchResponse,
)
from src.api.structured_location import StructuredLocationService
from src.api.routers.cache import create_cache_router
from src.api.routers.catalog import create_catalog_router
from src.api.discovery import DiscoveryService
from src.api.routers.search import create_search_router
from src.api.routers.corpus import create_corpus_router
from src.api.routers.evaluations import create_evaluation_router
from src.api.routers.health import create_health_router
from src.api.routers.sessions import create_session_router
from src.api.routers.system import create_system_router
from src.api.routers.registries import create_registry_router
from src.api.routers.collections import create_collections_router
from src.api.routers.pipeline import create_pipeline_router
from src.api.routers.workspace_transfer import create_workspace_transfer_router
from src.api.pipeline import PipelineService
from src.api.registry import RegistryService
from src.api.schemas import (
    DecomposedQueryResponse,
    QueryInterpretation,
    QueryRequest,
    QueryResponse,
    RetrievalInspectRequest,
    SourceChunk,
    SubQueryInfo,
)
from src.workspace.collections import SQLiteCollectionRepository
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository
from src.workspace.transfer import WorkspaceTransferService

import json as json_lib
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

# Setup structured logging (use json_mode=True in production)
setup_logging(level="INFO", json_mode=False)
logger = logging.getLogger(__name__)

# Global dictionary for pipeline storage — populated at startup, used in endpoints.
_state: dict[str, Any] = {}
# The canonical section order lives with the catalog aggregation; this name
# remains importable from the application boundary for compatibility.
SUPPORTED_SECTIONS = catalog_sections
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
structured_reader = StructuredDocumentService(original_viewer)
structured_locations = StructuredLocationService(original_viewer, structured_reader)


def _workspace_transfer_service() -> WorkspaceTransferService:
    """Open the explicitly configured local workspace after API-001 authorization."""
    database = WorkspaceDatabase.from_settings(settings)
    database.initialize()
    return WorkspaceTransferService(database)


def _collections_repository() -> SQLiteCollectionRepository:
    """Open the same local workspace for typed collection work.

    Construction happens only after the API-001 access boundary granted local
    workspace access, exactly like the transfer service, so a public deployment
    never opens the private database.
    """
    database = WorkspaceDatabase.from_settings(settings)
    database.initialize()
    return SQLiteCollectionRepository(database)


def _pipeline_service() -> PipelineService:
    """Open the private job store only after a pipeline route authorizes access."""
    return PipelineService(SQLiteJobRepository.from_settings(settings), settings)


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
                "report_date": chunk.get("report_date"),
                "accession_number": chunk.get("accession_number"),
                "sections": set(),
                "chunk_count": 0,
                "source_url": sanitize_sec_browser_url(chunk.get("source_url") or chunk.get("filing_url")),
            },
        )
        if chunk.get("section"):
            row["sections"].add(chunk["section"])
        if row["report_date"] != chunk.get("report_date"):
            row["report_date"] = None
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


def _catalog_rows_or_unavailable() -> list[dict[str, Any]]:
    """Return catalog rows, or refuse instead of reporting an empty corpus."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    return _document_catalog()


def _registry_catalog_rows() -> list[dict[str, Any]] | None:
    """Return the loaded catalog or an explicit unavailable registry source."""
    if _state.get("pipeline") is None:
        return None
    return _document_catalog()


# Bounds for the inspection scope block: enough for the served corpus, with an
# explicit truncation flag so the list is never mistaken for the full set.
INSPECT_ELIGIBLE_DOCUMENT_LIMIT = 200


def _inspect_chunk_filter(
    *,
    document_id: str | None,
    filing_date: str | None,
    year: int | None,
):
    """Build the document/date restriction production identity defines.

    The canonical document id and filing-year rules are reused, so an
    inspection filter can never disagree with the catalog or with discovery.
    Returns None when no document/date filter was requested, which keeps the
    legacy behaviour byte-identical.
    """
    if document_id is None and filing_date is None and year is None:
        return None

    def predicate(chunk: dict[str, Any]) -> bool:
        if document_id is not None and _document_id(chunk) != document_id:
            return False
        if filing_date is not None and chunk.get("filing_date") != filing_date:
            return False
        if year is not None and filing_year(chunk) != year:
            return False
        return True

    return predicate


def _inspect_scope(
    *,
    ticker: str | None,
    section: str | None,
    document_id: str | None,
    filing_date: str | None,
    year: int | None,
) -> dict[str, Any]:
    """Describe the effective inspection scope from the real catalog.

    The eligible set uses the same catalog filter the document routes use, so
    it reports the documents that genuinely match the applied scope.
    """
    try:
        rows = _catalog_rows_or_unavailable()
    except HTTPException:
        return {
            "documents": None,
            "eligible_document_ids": [],
            "truncated": False,
            "reason": "The catalog is unavailable.",
        }
    eligible = filter_documents(
        rows,
        ticker=ticker,
        section=section,
        filing_date=filing_date,
        year=year,
    )
    if document_id is not None:
        eligible = [row for row in eligible if row["document_id"] == document_id]
    ids = sorted(str(row["document_id"]) for row in eligible)
    return {
        "documents": len(ids),
        "eligible_document_ids": ids[:INSPECT_ELIGIBLE_DOCUMENT_LIMIT],
        "truncated": len(ids) > INSPECT_ELIGIBLE_DOCUMENT_LIMIT,
        "reason": None,
    }


def _discovery_service() -> DiscoveryService:
    """Return the shared provider-free discovery service.

    It borrows the loaded corpus and the retriever's already-built BM25 index,
    so a discovery search never embeds a query, runs a cross-encoder, calls a
    provider, or reads SEC. The bounded snapshot store lives for the process.
    """
    service = _state.get("discovery")
    if isinstance(service, DiscoveryService):
        return service
    pipeline = _get_pipeline()
    retriever = getattr(pipeline, "retriever", None)
    service = DiscoveryService(
        chunks=_loaded_retrieval_chunks,
        catalog_rows=_catalog_rows_or_unavailable,
        tokenize=getattr(retriever, "tokenize_query"),
        score=getattr(retriever, "bm25_scores"),
        present=getattr(retriever, "bm25_terms_present", None),
        document_id_of=_document_id,
    )
    _state["discovery"] = service
    return service


def _find_document_row(document_id: str) -> dict[str, Any] | None:
    return next((item for item in _document_catalog() if item["document_id"] == document_id), None)


def _raise_original_viewer_error(error: OriginalViewerError) -> None:
    raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message}) from error


def _pdf_store() -> PdfStore:
    return PdfStore(Path(settings.pdf_artifacts_dir))


def _pdf_primary_source(row: dict[str, Any]) -> tuple[Any, str] | None:
    """Resolve the primary available filing source for PDF rendering."""
    try:
        snapshot = original_viewer.snapshot(row)
    except OriginalViewerError:
        return None
    for source in snapshot.sources:
        if source.role == "primary_filing" and source.status == "available" and source.document_revision and source.normalized_text:
            return source, snapshot.source_set_revision
    for source in snapshot.sources:
        if source.status == "available" and source.document_revision and source.normalized_text:
            return source, snapshot.source_set_revision
    return None


def _pdf_identity(document_id: str, source: Any, source_set_revision: str) -> PdfArtifactIdentity:
    content_hash = source_content_hash(str(source.normalized_text or ""))
    if not content_hash or not source.document_revision:
        raise OriginalViewerError("source_unavailable", "The verified source has no stable render identity.", 409)
    return PdfArtifactIdentity(
        representation_type="DERIVED_PDF",
        document_id=document_id,
        source_document_id=source.source_document_id,
        source_set_revision=source_set_revision,
        document_revision=source.document_revision or "",
        source_content_hash=content_hash,
    )


def _pdf_stable_key(document_id: str, source_document_id: str, source_set_revision: str, document_revision: str) -> str:
    import hashlib

    profile = _pdf_identity_probe_profile()
    payload = "|".join([document_id, source_document_id, source_set_revision, document_revision, profile[0], profile[1]])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _pdf_identity_probe_profile() -> tuple[str, str]:
    from src.api.pdf_representation import RENDERER_TEMPLATE_VERSION, RENDERER_VERSION

    return RENDERER_VERSION, RENDERER_TEMPLATE_VERSION


def _pdf_family_key(document_id: str, source_document_id: str) -> str:
    """Marker key shared by every revision of one document/source binding."""
    import hashlib

    renderer_version, template_version = _pdf_identity_probe_profile()
    payload = "|".join([document_id, source_document_id, renderer_version, template_version])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _pdf_reader_availability(row: dict[str, Any], document_id: str) -> dict[str, Any]:
    """Cheap PDF availability for the reader manifest via the latest marker."""
    if not settings.pdf_generation_enabled:
        return {"status": "unsupported", "reason_code": "pdf_representation_unavailable", "reason": "PDF generation is disabled in this deployment."}
    resolved = _pdf_primary_source(row)
    if resolved is None:
        return {"status": "unavailable", "reason_code": "source_unavailable", "reason": "No admitted local source is available for this document."}
    source, source_set_revision = resolved
    family_key = _pdf_family_key(document_id, source.source_document_id)
    store = _pdf_store()
    generation_state = store.read_generation_state(family_key)
    if generation_state and generation_state.get("status") == "generating":
        return {"status": "generating", "reason_code": "pdf_generating", "reason": "PDF generation is in progress for this document."}
    if generation_state and generation_state.get("status") == "failed":
        return {"status": "failed", "reason_code": "pdf_generation_failed", "reason": str(generation_state.get("reason") or "The previous generation attempt failed.")}
    latest = store.read_latest(family_key)
    if latest is None:
        failure = store.load_failure(family_key)
        if failure:
            return {"status": "failed", "reason_code": "pdf_generation_failed", "reason": str(failure.get("reason") or "The previous generation attempt failed.")}
        return {"status": "supported", "reason_code": "pdf_supported", "reason": "A derived PDF can be generated from the verified local source."}
    current_source_hash = source_content_hash(str(source.normalized_text or ""))
    if (
        latest.get("source_set_revision") != source_set_revision
        or latest.get("document_revision") != (source.document_revision or "")
        or latest.get("source_content_hash") != current_source_hash
    ):
        return {"status": "stale", "reason_code": "pdf_stale", "reason": "The stored PDF was generated from a different source revision."}
    artifact_key = latest.get("artifact_key")
    stored = store.load_manifest(str(artifact_key)) if artifact_key else None
    if stored is None or not store.artifact_path(str(artifact_key)).is_file():
        return {"status": "failed", "reason_code": "pdf_generation_failed", "reason": "The current PDF manifest or artifact bytes are missing."}
    return {
        "status": "available",
        "reason_code": "pdf_available",
        "reason": "A derived PDF artifact is available for the current source revision.",
        "representation_id": stored.representation_id,
        "representation_type": stored.representation_type,
        "page_semantics": stored.page_semantics,
        "artifact_key": stored.artifact_key,
        "artifact_hash": stored.artifact_hash,
        "source_content_hash": stored.source_content_hash,
        "page_count": stored.page_count,
        "mapping_status": stored.mapping_status,
    }


def _pdf_base_manifest(
    document_id: str,
    source_document_id: str,
    source_set_revision: str,
    document_revision: str,
    content_hash: str | None = None,
) -> PdfRepresentationManifest:
    return PdfRepresentationManifest(
        representation_id=f"derived_pdf:pending:{document_id}",
        artifact_status="unavailable",
        document_id=document_id,
        source_document_id=source_document_id or None,
        source_set_revision=source_set_revision or None,
        document_revision=document_revision or None,
        source_content_hash=content_hash,
    )


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
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "If-Match",
        "Last-Event-ID",
        "ngrok-skip-browser-warning",
    ],
    expose_headers=["ETag"],
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
        source_url=sanitize_sec_browser_url(getattr(chunk, "source_url", None)),
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


app.include_router(create_health_router(_health_payload))
app.include_router(create_workspace_transfer_router(_workspace_transfer_service))
app.include_router(create_collections_router(_collections_repository))


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


app.include_router(
    create_corpus_router(lambda: _load_supported_tickers(), SUPPORTED_SECTIONS)
)


@app.get("/documents")
async def documents(
    ticker: str | None = Query(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$"),
    section: str | None = Query(default=None),
    filing_date: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=1900, le=2200),
    search: str | None = Query(default=None, max_length=100),
    sort: str = Query(default=DEFAULT_SORT),
    direction: str = Query(default="asc", pattern=r"^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict:
    """Return a paginated catalog derived from loaded retrieval metadata."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    if sort not in SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported sort field. Supported fields: {', '.join(SORT_FIELDS)}",
        )
    rows = _document_catalog()
    filtered = filter_documents(
        rows,
        ticker=ticker,
        section=section,
        year=year,
        filing_date=filing_date,
        search=search,
    )
    ordered = sort_documents(filtered, sort=sort, direction=direction)
    start = (page - 1) * page_size
    return {
        "items": ordered[start : start + page_size],
        "total": len(ordered),
        "page": page,
        "page_size": page_size,
        "sort": sort,
        "direction": direction,
    }


# Static catalog routes must be registered before the dynamic document routes
# so /documents/facets and /documents/stats can never resolve as a document_id.
app.include_router(create_catalog_router(_catalog_rows_or_unavailable))


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
                "source_url": sanitize_sec_browser_url(chunk.get("source_url") or chunk.get("filing_url")),
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
    document_row = _find_document_row(document_id)
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
        "chunk_text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_preview": text[:500],
        "text_length": len(text),
        "source_url": sanitize_sec_browser_url(chunk.get("source_url") or chunk.get("filing_url")),
        "sec_index_url": sec_index_url_for_document(document_row) if document_row else None,
        "presentation": build_chunk_presentation(text, chunk.get("section")),
    }


@app.get("/documents/{document_id}/original")
async def original_manifest(document_id: str) -> dict[str, Any]:
    """Return bounded local original-source availability without exposing paths."""
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"manifest:{document_id}",
            lambda: original_viewer.manifest(row),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


@app.get("/documents/{document_id}/reader", response_model=ReaderManifest)
async def reader_manifest(document_id: str) -> dict[str, Any]:
    """Return the typed local reader identity and representation manifest."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"reader:{document_id}",
            lambda: build_reader_manifest(
                row,
                viewer=original_viewer,
                structured_reader=structured_reader,
                pdf_availability=_pdf_reader_availability(row, document_id),
            ),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


def _reader_row_or_404(document_id: str) -> dict[str, Any]:
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return row


@app.get("/documents/{document_id}/reader/outline", response_model=StructuredOutlineResponse)
async def reader_outline(
    document_id: str,
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=50),
) -> dict[str, Any]:
    """Return a bounded outline from one revision-bound source."""
    row = _reader_row_or_404(document_id)
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"reader-outline:{document_id}:{source_document_id}:{source_set_revision}:{document_revision}:{cursor}:{limit}",
            lambda: structured_reader.outline(row, source_document_id, source_set_revision, document_revision, cursor, limit),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


@app.get("/documents/{document_id}/reader/content", response_model=StructuredContentResponse)
async def reader_content(
    document_id: str,
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=64, ge=1, le=64),
) -> dict[str, Any]:
    """Return bounded application-owned structured blocks, never raw HTML."""
    row = _reader_row_or_404(document_id)
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"reader-content:{document_id}:{source_document_id}:{source_set_revision}:{document_revision}:{cursor}:{limit}",
            lambda: structured_reader.content(row, source_document_id, source_set_revision, document_revision, cursor, limit),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


@app.get("/documents/{document_id}/reader/search", response_model=StructuredSearchResponse)
async def reader_search(
    document_id: str,
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
    q: str = Query(..., min_length=2, max_length=200),
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, Any]:
    """Search only the selected structured source."""
    row = _reader_row_or_404(document_id)
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"reader-search:{document_id}:{source_document_id}:{source_set_revision}:{document_revision}:{q}:{cursor}:{limit}",
            lambda: structured_reader.search(row, source_document_id, source_set_revision, document_revision, q, cursor, limit),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


@app.get("/documents/{document_id}/reader/section-export")
async def reader_section_export(
    document_id: str,
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
    format: Literal["html", "markdown"] = Query(default="html"),
) -> Response:
    """Export application-generated escaped structured content only."""
    row = _reader_row_or_404(document_id)
    try:
        payload, media_type = await run_in_threadpool(
            original_viewer.run,
            f"reader-export:{document_id}:{source_document_id}:{source_set_revision}:{document_revision}:{format}",
            lambda: structured_reader.export(row, source_document_id, source_set_revision, document_revision, format),
        )
        extension = "md" if format == "markdown" else "html"
        return Response(content=payload, media_type=media_type, headers={"Content-Disposition": f"attachment; filename=structured-section.{extension}"})
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


@app.get("/documents/{document_id}/pdf")
async def pdf_representation_status(document_id: str) -> dict[str, Any]:
    """Report the truthful derived-PDF status for one document."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not settings.pdf_generation_enabled:
        manifest = _pdf_base_manifest(document_id, "", "", "")
        manifest.artifact_status = "unsupported"
        manifest.reason = "PDF generation is disabled in this deployment."
        return manifest.model_dump(mode="json")
    resolved = _pdf_primary_source(row)
    if resolved is None:
        manifest = _pdf_base_manifest(document_id, "", "", "")
        manifest.artifact_status = "unavailable"
        manifest.reason = "No admitted local source is available for this document."
        return manifest.model_dump(mode="json")
    source, source_set_revision = resolved
    current_source_hash = source_content_hash(str(source.normalized_text or ""))
    family_key = _pdf_family_key(document_id, source.source_document_id)
    store = _pdf_store()
    generation_state = store.read_generation_state(family_key)
    if generation_state and generation_state.get("status") in {"generating", "failed", "stale"}:
        manifest = _pdf_base_manifest(document_id, source.source_document_id, source_set_revision, source.document_revision or "", current_source_hash)
        manifest.artifact_status = generation_state["status"]
        default_reason = (
            "PDF generation is in progress."
            if generation_state.get("status") == "generating"
            else "The previous PDF generation attempt did not produce a current artifact."
        )
        manifest.reason = str(generation_state.get("reason") or default_reason)
        return manifest.model_dump(mode="json")
    latest = store.read_latest(family_key)
    if latest is None:
        failure = store.load_failure(family_key)
        manifest = _pdf_base_manifest(document_id, source.source_document_id, source_set_revision, source.document_revision or "", current_source_hash)
        if failure:
            manifest.artifact_status = "failed"
            manifest.reason = str(failure.get("reason") or "The previous generation attempt failed.")
        else:
            manifest.artifact_status = "supported"
            manifest.reason = "A derived PDF can be generated from the verified local source."
        return manifest.model_dump(mode="json")
    manifest = _pdf_base_manifest(document_id, str(latest.get("source_document_id")), str(latest.get("source_set_revision")), str(latest.get("document_revision")), current_source_hash)
    if (
        latest.get("source_set_revision") != source_set_revision
        or latest.get("document_revision") != (source.document_revision or "")
        or latest.get("source_content_hash") != current_source_hash
    ):
        manifest.artifact_status = "stale"
        manifest.reason = "The stored PDF was generated from a different source revision. Generate again to refresh it."
        return manifest.model_dump(mode="json")
    artifact_key = str(latest.get("artifact_key") or "")
    stored = store.load_manifest(artifact_key) if artifact_key else None
    artifact_path = store.artifact_path(artifact_key) if artifact_key else None
    if stored is None or artifact_path is None or not artifact_path.is_file():
        manifest.artifact_status = "failed"
        manifest.reason = "The current PDF manifest or artifact bytes are missing."
        return manifest.model_dump(mode="json")
    actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if stored.artifact_hash != actual_hash or stored.source_content_hash != current_source_hash:
        manifest.artifact_status = "failed"
        manifest.reason = "The current PDF artifact bytes do not match their manifest hash."
        return manifest.model_dump(mode="json")
    manifest.artifact_status = "available"
    manifest.source_content_hash = latest.get("source_content_hash")
    manifest.artifact_key = artifact_key
    manifest.artifact_hash = actual_hash
    manifest.representation_id = stored.representation_id
    manifest.representation_type = stored.representation_type
    manifest.page_semantics = stored.page_semantics
    manifest.artifact_size_bytes = stored.artifact_size_bytes
    manifest.page_count = stored.page_count
    manifest.renderer = stored.renderer
    manifest.generated_at = stored.generated_at
    manifest.mapping_manifest_id = stored.mapping_manifest_id
    manifest.mapping_status = stored.mapping_status
    manifest.mapping_entry_count = stored.mapping_entry_count
    manifest.reason = stored.reason
    return manifest.model_dump(mode="json")


@app.post("/documents/{document_id}/pdf")
@limiter.limit("20/minute")
async def pdf_generate(request: Request, document_id: str) -> dict[str, Any]:
    """Generate (or regenerate) the derived PDF for one verified document."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not settings.pdf_generation_enabled:
        raise HTTPException(status_code=409, detail={"code": "pdf_unsupported", "message": "PDF generation is disabled in this deployment."})
    resolved = _pdf_primary_source(row)
    if resolved is None:
        raise HTTPException(status_code=409, detail={"code": "source_unavailable", "message": "No admitted local source is available for this document."})
    source, source_set_revision = resolved
    family_key = _pdf_family_key(document_id, source.source_document_id)
    store = _pdf_store()
    current_availability = _pdf_reader_availability(row, document_id)
    if current_availability.get("status") == "available":
        current_key = current_availability.get("artifact_key")
        current_manifest = store.load_manifest(str(current_key)) if current_key else None
        if current_manifest is not None and store.artifact_path(str(current_key)).is_file():
            return current_manifest.model_dump(mode="json")
    if current_availability.get("status") == "generating":
        raise HTTPException(status_code=409, detail={"code": "pdf_generation_busy", "message": "PDF generation is already in progress for this document."})
    store.write_generation_state(family_key, "generating")
    try:
        manifest, mapping, pdf_bytes = await run_in_threadpool(
            generate_derived_pdf,
            row,
            document_id=document_id,
            source=source,
            source_set_revision=source_set_revision,
            timeout_seconds=settings.pdf_generation_timeout_seconds,
            store=store,
        )
    except PdfGenerationBusy as error:
        raise HTTPException(status_code=409, detail={"code": "pdf_generation_busy", "message": error.message}) from error
    except PdfGenerationError as error:
        store.record_failure(family_key, error.message)
        store.write_generation_state(family_key, "failed", reason=error.message)
        raise HTTPException(status_code=error.http_status, detail={"code": error.code, "message": error.message}) from error
    fresh_resolved = _pdf_primary_source(row)
    if (
        fresh_resolved is None
        or fresh_resolved[1] != source_set_revision
        or fresh_resolved[0].source_document_id != source.source_document_id
        or fresh_resolved[0].document_revision != source.document_revision
        or source_content_hash(str(fresh_resolved[0].normalized_text or "")) != source_content_hash(str(source.normalized_text or ""))
    ):
        reason = "The verified source changed while the PDF was being generated; no artifact was published."
        store.write_generation_state(family_key, "stale", reason=reason)
        raise HTTPException(status_code=409, detail={"code": "source_changed", "message": reason})
    try:
        store.promote(manifest.artifact_key or "", pdf_bytes, manifest, mapping)
    except ValueError as error:
        store.record_failure(family_key, str(error))
        store.write_generation_state(family_key, "failed", reason=str(error))
        raise HTTPException(status_code=500, detail={"code": "artifact_invalid", "message": "The generated PDF failed artifact binding validation."}) from error
    store.write_latest(
        family_key,
        {
            "document_id": document_id,
            "source_document_id": source.source_document_id,
            "source_set_revision": source_set_revision,
            "document_revision": source.document_revision or "",
            "source_content_hash": manifest.source_content_hash,
            "artifact_key": manifest.artifact_key,
            "artifact_hash": manifest.artifact_hash,
            "artifact_status": "available",
            "representation_id": manifest.representation_id,
        },
    )
    store.clear_failure(family_key)
    store.clear_generation_state(family_key)
    return manifest.model_dump(mode="json")


@app.get("/documents/{document_id}/pdf/content")
async def pdf_content(document_id: str) -> Response:
    """Serve PDF bytes only when the artifact matches the current identity."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not settings.pdf_generation_enabled:
        raise HTTPException(status_code=409, detail={"code": "pdf_unsupported", "message": "PDF generation is disabled in this deployment."})
    resolved = _pdf_primary_source(row)
    if resolved is None:
        raise HTTPException(status_code=404, detail={"code": "source_unavailable", "message": "No admitted local source is available for this document."})
    source, source_set_revision = resolved
    try:
        identity = _pdf_identity(document_id, source, source_set_revision)
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)
    store = _pdf_store()
    family_key = _pdf_family_key(document_id, source.source_document_id)
    latest = store.read_latest(family_key)
    if latest is None:
        raise HTTPException(status_code=404, detail={"code": "pdf_not_generated", "message": "No derived PDF exists for this document yet."})
    if (
        latest.get("source_set_revision") != source_set_revision
        or latest.get("document_revision") != (source.document_revision or "")
        or latest.get("source_content_hash") != identity.source_content_hash
    ):
        raise HTTPException(status_code=409, detail={"code": "pdf_stale", "message": "The stored PDF was generated from a different source revision."})
    stored = store.load_manifest(identity.artifact_key())
    if stored is None or stored.source_content_hash != identity.source_content_hash:
        raise HTTPException(status_code=409, detail={"code": "pdf_stale", "message": "The stored PDF does not match the current source identity."})
    artifact_path = store.artifact_path(identity.artifact_key())
    if not artifact_path.is_file():
        raise HTTPException(status_code=404, detail={"code": "pdf_artifact_missing", "message": "The PDF artifact bytes are missing."})
    actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if stored.artifact_hash != actual_hash:
        raise HTTPException(status_code=409, detail={"code": "pdf_stale", "message": "The PDF artifact bytes do not match their manifest hash."})
    manifest = stored
    filename = f"{(row.get('ticker') or 'SEC')}_10-K_generated.pdf".replace('"', "")
    return FileResponse(
        artifact_path,
        media_type="application/pdf",
        headers={
            "ETag": f'"{manifest.artifact_hash}"',
            "X-Artifact-Key": identity.artifact_key(),
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


def _pdf_mapping_artifact(
    document_id: str,
    row: dict[str, Any],
) -> tuple[PdfArtifactIdentity, PdfRepresentationManifest, PdfMappingManifest]:
    """Resolve and validate the current PDF plus its hash-bound mapping."""
    resolved = _pdf_primary_source(row)
    if resolved is None:
        raise HTTPException(status_code=404, detail={"code": "source_unavailable", "message": "No admitted local source is available for this document."})
    source, source_set_revision = resolved
    try:
        identity = _pdf_identity(document_id, source, source_set_revision)
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)
    store = _pdf_store()
    family_key = _pdf_family_key(document_id, source.source_document_id)
    latest = store.read_latest(family_key)
    if latest is None:
        raise HTTPException(status_code=404, detail={"code": "pdf_not_generated", "message": "No derived PDF exists for this document yet."})
    if (
        latest.get("artifact_key") != identity.artifact_key()
        or latest.get("source_document_id") != identity.source_document_id
        or latest.get("source_set_revision") != identity.source_set_revision
        or latest.get("document_revision") != identity.document_revision
        or latest.get("source_content_hash") != identity.source_content_hash
    ):
        raise HTTPException(status_code=409, detail={"code": "pdf_stale", "message": "The stored PDF was generated from a different source revision."})
    manifest = store.load_manifest(identity.artifact_key())
    mapping = store.load_mapping(identity.artifact_key())
    artifact_path = store.artifact_path(identity.artifact_key())
    if manifest is None or mapping is None or not artifact_path.is_file():
        raise HTTPException(status_code=409, detail={"code": "pdf_mapping_missing", "message": "The current PDF artifact or its mapping sidecar is missing."})
    actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if (
        manifest.artifact_key != identity.artifact_key()
        or manifest.artifact_hash != actual_hash
        or manifest.source_document_id != identity.source_document_id
        or manifest.source_set_revision != identity.source_set_revision
        or manifest.document_revision != identity.document_revision
        or manifest.source_content_hash != identity.source_content_hash
        or mapping.artifact_key != identity.artifact_key()
        or mapping.artifact_hash != actual_hash
        or mapping.representation_id != manifest.representation_id
        or mapping.document_id != document_id
        or mapping.source_document_id != identity.source_document_id
        or mapping.source_content_hash != identity.source_content_hash
        or mapping.source_set_revision != identity.source_set_revision
        or mapping.document_revision != identity.document_revision
    ):
        raise HTTPException(status_code=409, detail={"code": "pdf_mapping_stale", "message": "The PDF mapping does not match the current artifact identity."})
    return identity, manifest, mapping


@app.get("/documents/{document_id}/pdf/mapping", response_model=PdfMappingManifest)
async def pdf_mapping(document_id: str) -> PdfMappingManifest:
    """Return only the mapping sidecar bound to the current PDF artifact."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not settings.pdf_generation_enabled:
        raise HTTPException(status_code=409, detail={"code": "pdf_unsupported", "message": "PDF generation is disabled in this deployment."})
    _identity, _manifest, mapping = _pdf_mapping_artifact(document_id, row)
    return mapping


@app.get("/documents/{document_id}/pdf/mapping/location", response_model=PdfEvidenceLocation)
async def pdf_mapping_location(
    document_id: str,
    chunk_id: str = Query(..., min_length=1, max_length=256),
    chunk_text_hash: str = Query(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
) -> PdfEvidenceLocation:
    """Resolve a citation to PDF rectangles only when block boundaries prove it."""
    if _state.get("pipeline") is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not settings.pdf_generation_enabled:
        raise HTTPException(status_code=409, detail={"code": "pdf_unsupported", "message": "PDF generation is disabled in this deployment."})
    identity, manifest, mapping = _pdf_mapping_artifact(document_id, row)
    base = {
        "document_id": document_id,
        "source_document_id": identity.source_document_id,
        "source_set_revision": identity.source_set_revision,
        "document_revision": identity.document_revision,
        "source_content_hash": identity.source_content_hash,
        "representation_id": manifest.representation_id,
        "artifact_key": identity.artifact_key(),
        "artifact_hash": mapping.artifact_hash,
        "mapping_manifest_id": mapping.mapping_manifest_id,
        "chunk_id": chunk_id,
        "chunk_text_hash": chunk_text_hash,
    }
    if source_document_id != identity.source_document_id or source_set_revision != identity.source_set_revision or document_revision != identity.document_revision:
        return PdfEvidenceLocation(status="stale", reason="The selected source revision does not match the current PDF artifact.", **base)
    records = [record for record in _chunk_records_index().get(chunk_id, []) if record[0] == document_id]
    if not records:
        raise HTTPException(status_code=404, detail={"code": "chunk_not_found", "message": "Chunk not found for this document."})
    if len(records) > 1:
        return PdfEvidenceLocation(status="ambiguous", reason="The selected chunk identity is ambiguous for this document.", match_count=2, match_count_capped=True, **base)
    chunk_text = str(records[0][1].get("text") or "")
    if hashlib.sha256(chunk_text.encode("utf-8")).hexdigest() != chunk_text_hash:
        return PdfEvidenceLocation(status="stale", reason="The indexed chunk changed.", **base)
    resolved = _pdf_primary_source(row)
    if resolved is None:
        raise HTTPException(status_code=404, detail={"code": "source_unavailable", "message": "No admitted local source is available for this document."})
    source, _source_set_revision = resolved
    normalized_text = str(getattr(source, "normalized_text", None) or "")
    matches = whitespace_literal_matches(normalized_text, chunk_text)
    if not matches:
        return PdfEvidenceLocation(status="unavailable", reason="The full indexed chunk was not found in the rendered source text.", **base)
    if len(matches) > 1:
        return PdfEvidenceLocation(status="ambiguous", reason="The indexed chunk matches more than one source interval.", match_count=2, match_count_capped=True, **base)
    match_start, match_end = matches[0]
    entries = sorted(
        [entry for entry in mapping.entries if entry.char_end > match_start and entry.char_start < match_end],
        key=lambda entry: entry.block_index,
    )
    if not entries or any(entry.status != "exact" or not entry.rects for entry in entries):
        return PdfEvidenceLocation(status="unavailable", reason="The selected range has no complete PDF rectangle mapping.", **base)
    if entries[0].char_start != match_start or entries[-1].char_end != match_end:
        return PdfEvidenceLocation(status="unavailable", reason="The selected range does not align to stable rendered source blocks.", **base)
    cursor = entries[0].char_end
    for entry in entries[1:]:
        if normalized_text[cursor:entry.char_start].strip():
            return PdfEvidenceLocation(status="unavailable", reason="The selected range crosses an unmapped source boundary.", **base)
        cursor = entry.char_end
    if normalized_text[cursor:match_end].strip():
        return PdfEvidenceLocation(status="unavailable", reason="The selected range crosses an unmapped source boundary.", **base)
    return PdfEvidenceLocation(
        status="exact",
        match_count=1,
        entry_ids=[entry.block_id for entry in entries],
        rects=[rect for entry in entries for rect in entry.rects],
        reason=None,
        **base,
    )


@app.get("/documents/{document_id}/original/content")
async def original_content(
    document_id: str,
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
    start: int = Query(default=0, ge=0),
    limit: int = Query(default=16_000, ge=1, le=32_000),
    chunk_id: str | None = Query(default=None, max_length=256),
    chunk_text_hash: str | None = Query(default=None, max_length=128),
    find: str | None = Query(default=None, max_length=200),
) -> dict[str, Any]:
    """Return only a revision-bound normalized text window."""
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if (chunk_id is None) != (chunk_text_hash is None):
        raise HTTPException(status_code=422, detail={"code": "invalid_request", "message": "chunk_id and chunk_text_hash must be supplied together."})
    chunk_text: str | None = None
    if chunk_id is not None and chunk_text_hash is not None:
        records = _chunk_records_index().get(chunk_id, [])
        if not records:
            raise HTTPException(status_code=404, detail={"code": "chunk_not_found", "message": "Chunk not found."})
        if len(records) > 1:
            raise HTTPException(status_code=409, detail={"code": "chunk_ambiguous", "message": "Chunk ID is ambiguous."})
        chunk_text = str(records[0][1].get("text") or "")
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"content:{document_id}:{source_document_id}:{source_set_revision}:{document_revision}",
            lambda: original_viewer.content(
                row,
                source_document_id,
                source_set_revision,
                document_revision,
                start,
                limit,
                find,
                chunk_text,
                chunk_text_hash,
            ),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


@app.get("/chunks/{chunk_id}/original-location")
async def original_location(
    chunk_id: str,
    chunk_text_hash: str = Query(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
) -> dict[str, Any]:
    """Return only a unique, revision-bound original correspondence."""
    records = _chunk_records_index().get(chunk_id, [])
    if not records:
        raise HTTPException(status_code=404, detail={"code": "chunk_not_found", "message": "Chunk not found."})
    if len(records) > 1:
        raise HTTPException(status_code=409, detail={"code": "chunk_ambiguous", "message": "Chunk ID is ambiguous."})
    document_id, chunk = records[0]
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found."})
    chunk_text = str(chunk.get("text") or "")
    try:
        def locate() -> dict[str, Any]:
            snapshot = original_viewer.snapshot(row)
            if snapshot.source_set_revision != source_set_revision:
                raise OriginalViewerError("source_changed", "The original source set changed. Reload the viewer.")
            if hashlib.sha256(chunk_text.encode("utf-8")).hexdigest() != chunk_text_hash:
                raise OriginalViewerError("chunk_changed", "The indexed chunk changed. Reload the evidence.")
            presentation = build_chunk_presentation(chunk_text, chunk.get("section"))
            result = original_viewer.table_location(row, chunk_text, chunk_text_hash, source_set_revision) if presentation["kind"] == "markdown_table" else locate_chunk(snapshot, chunk_text, chunk_text_hash, source_set_revision)
            return {
                "chunk_id": chunk_id,
                "chunk_text_hash": chunk_text_hash,
                "document_id": document_id,
                "source_set_revision": source_set_revision,
                "matcher_version": "sec-viewer-location-v1",
                **result,
            }
        return await run_in_threadpool(original_viewer.run, f"location:{document_id}:{chunk_id}:{source_set_revision}", locate)
    except OriginalViewerError as error:
        if error.code == "chunk_changed":
            _raise_original_viewer_error(error)
        _raise_original_viewer_error(error)


@app.get("/chunks/{chunk_id}/reader-location", response_model=EvidenceLocation)
async def reader_location(
    chunk_id: str,
    chunk_text_hash: str = Query(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
) -> EvidenceLocation:
    """Return exact structured correspondence without fuzzy source selection."""
    records = _chunk_records_index().get(chunk_id, [])
    if not records:
        raise HTTPException(status_code=404, detail={"code": "chunk_not_found", "message": "Chunk not found."})
    if len(records) > 1:
        raise HTTPException(status_code=409, detail={"code": "chunk_ambiguous", "message": "Chunk ID is ambiguous."})
    document_id, chunk = records[0]
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found."})
    location = await run_in_threadpool(
        original_viewer.run,
        f"reader-location:{document_id}:{chunk_id}:{source_set_revision}",
        lambda: structured_locations.locate(
            row,
            chunk_id,
            str(chunk.get("text") or ""),
            chunk_text_hash,
            source_set_revision,
            str(chunk.get("section")) if chunk.get("section") is not None else None,
        ),
    )
    if location.status == "stale":
        raise HTTPException(status_code=409, detail=location.model_dump(mode="json"))
    return location


@app.get("/documents/{document_id}/original/search")
async def original_search(
    document_id: str,
    source_document_id: str = Query(..., min_length=1, max_length=128),
    source_set_revision: str = Query(..., min_length=1, max_length=128),
    document_revision: str = Query(..., min_length=1, max_length=128),
    q: str = Query(..., min_length=2, max_length=200),
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Find literal text in one selected normalized source document."""
    row = _find_document_row(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        return await run_in_threadpool(
            original_viewer.run,
            f"search:{document_id}:{source_document_id}:{source_set_revision}:{document_revision}:{q}:{cursor}:{limit}",
            lambda: original_viewer.search(
                row,
                source_document_id,
                source_set_revision,
                document_revision,
                q,
                cursor,
                limit,
            ),
        )
    except OriginalViewerError as error:
        _raise_original_viewer_error(error)


app.include_router(
    create_search_router(
        _discovery_service,
        limiter=limiter,
        rate_limit=settings.search_rate_limit,
    )
)
app.include_router(
    create_system_router(
        _get_pipeline,
        lambda: _state,
        lambda: app.version,
    )
)
app.include_router(
    create_registry_router(
        RegistryService(
            settings=settings,
            get_state=lambda: _state,
            get_catalog_rows=_registry_catalog_rows,
            get_chunks=lambda: _loaded_retrieval_chunks()
            if _state.get("pipeline") is not None
            else None,
        )
    )
)
app.include_router(create_pipeline_router(_pipeline_service))
app.include_router(create_evaluation_router())

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
            chunk_filter=_inspect_chunk_filter(
                document_id=body.document_id,
                filing_date=body.filing_date,
                year=body.year,
            ),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception("Retrieval inspection failed")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    chunk_records = _chunk_records_index()
    for candidate in trace.get("candidates", []):
        records = chunk_records.get(candidate.get("chunk_id"), [])
        candidate["document_id"] = records[0][0] if len(records) == 1 else None
    trace["candidate_count"] = len(trace.get("candidates", []))
    trace["selected_count"] = len(trace.get("selected_chunk_ids", []))
    trace["filter_values"] = {
        "ticker": ticker,
        "section": body.section,
        "document_id": body.document_id,
        "filing_date": body.filing_date,
        "year": body.year,
    }
    trace["scope"] = _inspect_scope(
        ticker=ticker,
        section=body.section,
        document_id=body.document_id,
        filing_date=body.filing_date,
        year=body.year,
    )
    return {
        "query_interpretation": _query_interpretation(original_question, normalized),
        "trace": trace,
    }


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


app.include_router(create_session_router(_get_pipeline))
app.include_router(
    create_cache_router(
        limiter,
        _get_pipeline,
        lambda: telemetry,
        _embed_query_pair,
    )
)


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
