"""
Module: rag_pipeline.py
Purpose: The single entry point for the RAG system — connects the Retriever and Generator.
(FastAPI) will only need to import RAGPipeline, nothing else.
"""

import logging

from src.generation.generator import Generator, RAGResponse
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, retriever: Retriever, generator: Generator):
        self.retriever = retriever
        self.generator = generator

    def query(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
    ) -> RAGResponse:
        logger.info("RAG query: '%s' (ticker=%s, section=%s)", question, ticker, section)
        chunks = self.retriever.retrieve(question, top_k=top_k, ticker=ticker, section=section)
        return self.generator.generate(question, chunks)

    def query_stream(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        conversation_history: list[dict] | None = None,
    ):
        """Generator: yield (event_type, data) tuples.
            event_type: 'sources' | 'token' | 'done' | 'error'
            Separate sources and tokens into two separate events so the client can
            render sources immediately while tokens are still streaming"""
        try:
            chunks = self.retriever.retrieve(
                question, top_k=top_k, ticker=ticker, section=section
            )

            # Submit sources BEFORE streaming tokens — client displays immediately
            sources_data = [
                {
                    "citation": c.citation,
                    "score": round(c.score, 4),
                    "text_preview": c.text[:200],
                }
                for c in chunks
            ]
            yield ("sources", sources_data)

            # Stream tokens
            for token in self.generator.generate_stream(question, chunks):
                yield ("token", token)

            yield ("done", None)

        except Exception as e:
            logger.exception("Error in query_stream: %s", e)
            yield ("error", str(e))
