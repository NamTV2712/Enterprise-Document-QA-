"""
Module: retriever.py
Purpose: The only class that external code needs to use to perform retrieval.
(LLM) only needs to import Retriever — regardless of whether Embedder or
VectorStore exists.
"""

import logging
from dataclasses import dataclass

from src.retrieval.embedder import Embedder
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Result returned from retrieval — only contains what Step 8 (LLM) needs.
    score: cosine similarity (0-1), higher = closer to the question in terms of semantics.
    citation: pre-formatted citation string for LLM to insert into the response.
    """
    chunk_id: str
    ticker: str
    section: str
    filing_date: str
    score: float
    text: str
    citation: str  # Example: "AAPL 10-K (2025-10-31), Section: Risk Factors"


class Retriever:
    def __init__(self, embedder: Embedder, store: VectorStore):
        # Receive dependency from outside (dependency injection) instead of
        # initializing internally — makes testing easier (can inject mock),
        # and avoids loading the model multiple times when multiple modules share the Retriever.
        self.embedder = embedder
        self.store = store

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
    ) -> list[RetrievedChunk]:
        """The only entry point for all retrieval requests.
        query: the user's English question (without prefix — Retriever adds it)
        top_k: the number of chunks to return
        ticker/section: optional filters — None means no filter
        """
        if not query.strip():
            logger.warning("Query is empty, returning empty results")
            return []

        query_vector = self.embedder.embed_query(query)
        raw_results = self.store.search(
            query_vector=query_vector,
            top_k=top_k,
            ticker=ticker,
            section=section,
        )

        chunks = [self._to_retrieved_chunk(r) for r in raw_results]
        logger.info(
            "Query '%s...' → %d chunk (top score: %.4f)",
            query[:50], len(chunks), chunks[0].score if chunks else 0,
        )
        return chunks

    @staticmethod
    def _to_retrieved_chunk(raw: dict) -> RetrievedChunk:
        section_label = raw["section"].replace("_", " ").title()
        citation = (
            f"{raw['ticker']} 10-K (filed {raw['filing_date']}), "
            f"Section: {section_label}"
        )
        return RetrievedChunk(
            chunk_id=raw["chunk_id"],
            ticker=raw["ticker"],
            section=raw["section"],
            filing_date=raw["filing_date"],
            score=raw["score"],
            text=raw["text"],
            citation=citation,
        )