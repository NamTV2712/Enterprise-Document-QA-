"""
Module: app.py
FastAPI application for RAG pipeline.
Design: Load all heavy objects (model, DB connection) at once
at startup via the lifespan context manager.
"""

import logging
import re
import time
import asyncio
import functools
import threading
import unicodedata
import uuid
from contextlib import asynccontextmanager
from typing import Any, Callable, Literal, TypeVar

import anyio.to_thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from configs.settings import settings
from configs.logging_config import setup_logging
from configs.tickers import TICKERS
from src.generation.generator import Generator
from src.generation.query_decomposer import QueryDecomposer
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_normalizer import normalize_retrieval_question
from src.retrieval.vector_store import VectorStore
from src.api.telemetry import RequestTelemetry
from src.api.proxy import get_rate_limit_key

import json as json_lib
from fastapi.responses import StreamingResponse

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
    retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=all_chunks)
    generator = Generator()
    pipeline = RAGPipeline(retriever=retriever, generator=generator)
    _state["pipeline"] = pipeline
    _state["decomposer"] = QueryDecomposer(pipeline=pipeline)
    _state["store"] = store
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


class SourceChunk(BaseModel):
    citation: str
    score: float
    text_preview: str  # First 200 characters for collapsed evidence previews.
    text: str | None = None
    chunk_id: str | None = None
    ticker: str | None = None
    section: str | None = None
    filing_date: str | None = None


class QueryResponse(BaseModel):
    answer: str
    model_used: str
    sources: list[SourceChunk]
    num_chunks_retrieved: int


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


class CacheTestRequest(BaseModel):
    query_a: str = Field(min_length=5)
    query_b: str = Field(min_length=5)


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
    return payload


def _source_chunk_payload(chunk: Any) -> SourceChunk:
    """Serialize one retrieved chunk consistently across all query routes."""
    return SourceChunk(
        citation=chunk.citation,
        score=round(chunk.score, 4),
        text_preview=chunk.text[:200],
        text=chunk.text,
        chunk_id=chunk.chunk_id,
        ticker=chunk.ticker,
        section=chunk.section,
        filing_date=chunk.filing_date,
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

    normalized = normalize_retrieval_question(_sanitize_question(body.question))
    ticker = body.ticker or normalized.detected_ticker
    try:
        response = await _run_query_with_timeout(
            pipeline.query,
            question=normalized.question,
            top_k=body.top_k,
            ticker=ticker,
            section=body.section,
            session_id=body.session_id,
        )
    except TimeoutError:
        logger.warning("Query timed out after %.1f seconds", QUERY_TIMEOUT_SECONDS)
        raise HTTPException(status_code=504, detail=QUERY_TIMEOUT_DETAIL)
    except Exception as e:
        logger.exception("Error occurred while processing query: %s", e)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    sources = [_source_chunk_payload(chunk) for chunk in response.retrieved_chunks]

    return QueryResponse(
        answer=response.answer,
        model_used=response.model_used,
        sources=sources,
        num_chunks_retrieved=len(response.retrieved_chunks),
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

    normalized = normalize_retrieval_question(_sanitize_question(body.question))
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
        )
    except TimeoutError:
        logger.warning(
            "Decomposed query timed out after %.1f seconds",
            DECOMPOSED_TIMEOUT_SECONDS,
        )
        raise HTTPException(status_code=504, detail=DECOMPOSED_TIMEOUT_DETAIL)
    except Exception as e:
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
        sources=[_source_chunk_payload(chunk) for chunk in result.all_chunks[:10]],
        num_total_chunks=len(result.all_chunks),
    )


@app.get("/supported-tickers")
async def supported_tickers() -> dict:
    """List of supported tickers — helps the UI/user know what they can ask about."""
    tickers = await run_in_threadpool(_load_supported_tickers)
    return {
        "tickers": tickers,
        "sections": SUPPORTED_SECTIONS,
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
    """Return conversation history for debugging and UI rendering."""
    _validate_session_id(session_id)
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    turns = pipeline.memory.get_history(session_id)
    return {
        "session_id": session_id,
        "turns": [
            {
                "user": turn.user_message,
                "assistant": turn.assistant_message,
                "rewritten_query": turn.rewritten_query,
            }
            for turn in turns
        ],
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
        queue: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue()
        cancel_event = threading.Event()

        def enqueue(event: tuple[str, Any] | None) -> None:
            if cancel_event.is_set():
                return
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                cancel_event.set()

        def run_stream() -> None:
            normalized = normalize_retrieval_question(request_body.question)
            ticker = request_body.ticker or normalized.detected_ticker
            try:
                for event_type, data in pipeline.query_stream(
                    question=normalized.question,
                    top_k=request_body.top_k,
                    ticker=ticker,
                    section=request_body.section,
                    session_id=request_body.session_id,
                    cancel_event=cancel_event,
                ):
                    if cancel_event.is_set():
                        break
                    safe_data = INTERNAL_ERROR_DETAIL if event_type == "error" else data
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
