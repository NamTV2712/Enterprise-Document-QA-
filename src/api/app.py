"""
Module: app.py
FastAPI application for RAG pipeline.
Design: Load all heavy objects (model, DB connection) at once
at startup via the lifespan context manager.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Literal
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from configs.settings import settings
from src.generation.generator import Generator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.embedder import Embedder
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Global dictionary for pipeline storage — populated at startup, used in endpoints.
_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run the code BEFORE yield when the server starts, and after yield when the server shuts down.
        This is the FastAPI pattern recommended as a replacement for @app.on_event('startup')."""
    logger.info("Initializing RAG pipeline...")
    t0 = time.time()

    embedder = Embedder()
    store = VectorStore(path=settings.data_processed_dir / "qdrant")
    retriever = Retriever(embedder=embedder, store=store)
    generator = Generator(provider="groq")
    _state["pipeline"] = RAGPipeline(retriever=retriever, generator=generator)
    _state["store"] = store

    logger.info("Pipeline ready after %.1f seconds", time.time() - t0)
    yield  # server running...

    # Cleanup
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


# --- Pydantic models cho request/response ---

class QueryRequest(BaseModel):
    question: str = Field(
        min_length=5, max_length=500,
        examples=["What was Apple's total revenue in 2024?"]
    )
    ticker: str | None = Field(
        default=None, pattern=r"^[A-Z]{1,5}$",
        examples=["AAPL"]
    )
    section: Literal["business", "risk_factors", "mdna", "financial_statements"] | None = Field(
        default=None,
        examples=["financial_statements"]
    )
    top_k: int = Field(default=5, ge=1, le=10)


class SourceChunk(BaseModel):
    citation: str
    score: float
    text_preview: str  # Just the first 200 characters — enough for the UI to display


class QueryResponse(BaseModel):
    answer: str
    model_used: str
    sources: list[SourceChunk]
    num_chunks_retrieved: int


# --- Endpoints ---

@app.get("/health")
async def health() -> dict:
    """Health check endpoint — used by Docker health check,
    load balancer, and monitoring in the future"""
    return {
        "status": "ok",
        "pipeline_ready": "pipeline" in _state,
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


@app.get("/supported-tickers")
async def supported_tickers() -> dict:
    """List of supported tickers — helps the UI/user know what they can ask about."""
    return {
        "tickers": ["AAPL", "MSFT", "AMZN"],
        "sections": ["business", "risk_factors", "mdna", "financial_statements"],
    }
