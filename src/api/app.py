"""
Module: app.py
FastAPI application for RAG pipeline.
Design: Load all heavy objects (model, DB connection) at once
at startup via the lifespan context manager.
"""

import logging
import time
import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Literal
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from configs.settings import settings
from configs.tickers import TICKERS
from src.generation.generator import Generator
from src.generation.query_decomposer import QueryDecomposer
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.vector_store import VectorStore

import json as json_lib
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Global dictionary for pipeline storage — populated at startup, used in endpoints.
_state: dict[str, Any] = {}
SUPPORTED_SECTIONS = [
    "business",
    "risk_factors",
    "mdna",
    "financial_statements",
    "financial_table",
]


def _load_supported_tickers() -> list[str]:
    tickers = []
    for ticker in TICKERS:
        ticker_dir = settings.data_processed_dir / ticker
        if any(path.stat().st_size > 0 for path in ticker_dir.glob("*_chunks_embedded.jsonl")):
            tickers.append(ticker)
    return tickers or TICKERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing hybrid RAG pipeline...")
    t0 = time.time()

    embedder = Embedder()
    store = VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    )
    all_chunks = load_embedded_chunks(settings.data_processed_dir)
    logger.info("Loaded %d chunks for BM25 index", len(all_chunks))

    retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=all_chunks)
    generator = Generator(provider="groq")
    pipeline = RAGPipeline(retriever=retriever, generator=generator)
    _state["pipeline"] = pipeline
    _state["decomposer"] = QueryDecomposer(pipeline=pipeline)
    _state["store"] = store

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
    allow_origins=["*"],  # Open for demo; narrow down in production
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    text_preview: str  # Just the first 200 characters — enough for the UI to display


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

@app.get("/health")
async def health() -> dict:
    """Health check endpoint — used by Docker health check,
    load balancer, and monitoring in the future"""
    pipeline: RAGPipeline | None = _state.get("pipeline")
    return {
        "status": "ok",
        "pipeline_ready": pipeline is not None,
        "memory": pipeline.memory.get_stats() if pipeline else {},
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Main endpoint: receive the question, return the answer + source citation"""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        # This shouldn't happen if the lifespan is running correctly — but it's a precaution
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    try:
        response = pipeline.query(
            question=request.question,
            top_k=request.top_k,
            ticker=request.ticker,
            section=request.section,
            session_id=request.session_id,
        )
    except Exception as e:
        logger.exception("Error occurred while processing query: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    sources = [
        SourceChunk(
            citation=chunk.citation,
            score=round(chunk.score, 4),
            text_preview=chunk.text[:200],
        )
        for chunk in response.retrieved_chunks
    ]

    return QueryResponse(
        answer=response.answer,
        model_used=response.model_used,
        sources=sources,
        num_chunks_retrieved=len(response.retrieved_chunks),
    )


@app.post("/query/decomposed", response_model=DecomposedQueryResponse)
async def query_decomposed(request: QueryRequest) -> DecomposedQueryResponse:
    """Handle complex or comparative questions with optional query decomposition.

    Simple questions fall back to the normal RAG pipeline. Complex questions are
    planned into focused sub-queries, retrieved independently, and synthesized
    into one grounded answer.
    """
    decomposer: QueryDecomposer | None = _state.get("decomposer")
    if decomposer is None:
        raise HTTPException(status_code=503, detail="The decomposer is not ready yet")

    try:
        result = decomposer.run(
            question=request.question,
            top_k=request.top_k,
            ticker=request.ticker,
            section=request.section,
            session_id=request.session_id,
        )
    except Exception as e:
        logger.exception("Error occurred while processing decomposed query: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

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
            SourceChunk(
                citation=chunk.citation,
                score=round(chunk.score, 4),
                text_preview=chunk.text[:200],
            )
            for chunk in result.all_chunks[:10]
        ],
        num_total_chunks=len(result.all_chunks),
    )


@app.get("/supported-tickers")
async def supported_tickers() -> dict:
    """List of supported tickers — helps the UI/user know what they can ask about."""
    return {
        "tickers": _load_supported_tickers(),
        "sections": SUPPORTED_SECTIONS,
    }


@app.delete("/session/{session_id}")
async def clear_session(session_id: str) -> dict:
    """Clear one conversation session."""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    pipeline.memory.clear_session(session_id)
    return {"cleared": session_id}


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str) -> dict:
    """Return conversation history for debugging and UI rendering."""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    turns = pipeline.memory.get_history(session_id)
    return {
        "session_id": session_id,
        "turns": [
            {
                "user": turn.user_message,
                "assistant": turn.assistant_message[:200],
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


@app.post("/cache/clear")
async def cache_clear() -> dict:
    """Clear semantic cache entries and reset cache metrics."""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")
    count = pipeline.cache.clear()
    return {"cleared_entries": count}


@app.post("/cache/test")
async def cache_test_similarity(request: CacheTestRequest) -> dict:
    """Compare two query embeddings to tune the semantic cache threshold."""
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    emb_a = pipeline.retriever.embedder.embed_query(request.query_a)
    emb_b = pipeline.retriever.embedder.embed_query(request.query_b)
    similarity = pipeline.cache.test_similarity(emb_a, emb_b)
    return {
        "query_a": request.query_a,
        "query_b": request.query_b,
        "similarity": round(similarity, 6),
        "threshold": pipeline.cache.threshold,
        "would_cache_hit": similarity >= pipeline.cache.threshold,
    }

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """Streaming endpoint using Server-Sent Events (SSE).

    Each event is emitted as `data: {json}\n\n` per the SSE spec.
    """
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="The pipeline is not ready yet")

    async def event_generator():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue()

        def run_stream() -> None:
            try:
                for event_type, data in pipeline.query_stream(
                    question=request.question,
                    top_k=request.top_k,
                    ticker=request.ticker,
                    section=request.section,
                    session_id=request.session_id,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, (event_type, data))
            except Exception as e:
                logger.exception("Unhandled streaming endpoint error: %s", e)
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=run_stream, daemon=True).start()

        while True:
            event = await queue.get()
            if event is None:
                break
            event_type, data = event
            try:
                payload = json_lib.dumps(
                    {"type": event_type, "data": data},
                    ensure_ascii=False
                )
                yield f"data: {payload}\n\n"
            except Exception as e:
                error_payload = json_lib.dumps({"type": "error", "data": str(e)})
                yield f"data: {error_payload}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering if deploying after reverse proxy
        },
    )
