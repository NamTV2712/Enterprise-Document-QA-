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