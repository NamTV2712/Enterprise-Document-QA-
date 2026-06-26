"""
Module: rag_pipeline.py
Purpose: The single entry point for the RAG system — connects the Retriever and Generator.
(FastAPI) will only need to import RAGPipeline, nothing else.
"""

import logging

from src.generation.generator import Generator, RAGResponse
from src.retrieval.retriever import Retriever
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.semantic_cache import CacheEntry, SemanticCache

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever,
        generator: Generator,
        cache: SemanticCache | None = None,
    ):
        self.retriever = retriever
        self.generator = generator
        self.cache = cache or SemanticCache()

    def _embed_query_once(self, question: str) -> list[float]:
        return self.retriever.embedder.embed_query(question)

    def _retrieve_with_optional_embedding(
        self,
        question: str,
        query_embedding: list[float],
        top_k: int,
        ticker: str | None,
        section: str | None,
    ) -> list[RetrievedChunk]:
        if hasattr(self.retriever, "retrieve_with_embedding"):
            return self.retriever.retrieve_with_embedding(
                query=question,
                query_embedding=query_embedding,
                top_k=top_k,
                ticker=ticker,
                section=section,
            )
        return self.retriever.retrieve(question, top_k=top_k, ticker=ticker, section=section)

    @staticmethod
    def _chunks_to_dicts(chunks: list[RetrievedChunk]) -> list[dict]:
        return [
            {
                "chunk_id": chunk.chunk_id,
                "ticker": chunk.ticker,
                "section": chunk.section,
                "filing_date": chunk.filing_date,
                "score": chunk.score,
                "text": chunk.text,
                "citation": chunk.citation,
            }
            for chunk in chunks
        ]

    @staticmethod
    def _chunks_from_cache(cached: CacheEntry) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id=source["chunk_id"],
                ticker=source["ticker"],
                section=source["section"],
                filing_date=source["filing_date"],
                score=source["score"],
                text=source["text"],
                citation=source["citation"],
            )
            for source in cached.sources
        ]

    @staticmethod
    def _sources_for_stream(chunks: list[RetrievedChunk]) -> list[dict]:
        return [
            {
                "citation": chunk.citation,
                "score": round(chunk.score, 4),
                "text_preview": chunk.text[:200],
                "chunk_id": chunk.chunk_id,
                "ticker": chunk.ticker,
                "section": chunk.section,
                "filing_date": chunk.filing_date,
                "text": chunk.text,
            }
            for chunk in chunks
        ]

    def query(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
    ) -> RAGResponse:
        logger.info("RAG query: '%s...' (ticker=%s, section=%s)", question[:50], ticker, section)
        query_embedding = self._embed_query_once(question)

        cached = self.cache.get(query_embedding, ticker, section, top_k)
        if cached:
            return RAGResponse(
                answer=cached.answer,
                retrieved_chunks=self._chunks_from_cache(cached),
                model_used=f"{cached.model_used} (cached)",
            )

        chunks = self._retrieve_with_optional_embedding(
            question=question,
            query_embedding=query_embedding,
            top_k=top_k,
            ticker=ticker,
            section=section,
        )
        response = self.generator.generate(question, chunks)
        self.cache.set(
            query_embedding=query_embedding,
            ticker=ticker,
            section=section,
            top_k=top_k,
            answer=response.answer,
            sources=self._chunks_to_dicts(chunks),
            model_used=response.model_used,
        )
        return response

    def query_stream(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        conversation_history: list[dict] | None = None,
    ):
        """Yield SSE-compatible event tuples.

        Cache hits replay sources and answer tokens without calling the LLM.
        Cache misses run retrieval and LLM streaming, then store the full answer.
        """
        try:
            query_embedding = self._embed_query_once(question)
            cached = self.cache.get(query_embedding, ticker, section, top_k)
            if cached:
                logger.info("Stream cache HIT for '%s...'", question[:50])
                yield ("sources", self._sources_for_stream(self._chunks_from_cache(cached)))
                words = cached.answer.split(" ")
                for index, word in enumerate(words):
                    token = word if index == len(words) - 1 else f"{word} "
                    yield ("token", token)
                yield ("done", None)
                return

            chunks = self._retrieve_with_optional_embedding(
                question=question,
                query_embedding=query_embedding,
                top_k=top_k,
                ticker=ticker,
                section=section,
            )

            sources_data = self._sources_for_stream(chunks)
            yield ("sources", sources_data)

            full_answer = ""
            for token in self.generator.generate_stream(question, chunks):
                full_answer += token
                yield ("token", token)

            self.cache.set(
                query_embedding=query_embedding,
                ticker=ticker,
                section=section,
                top_k=top_k,
                answer=full_answer,
                sources=self._chunks_to_dicts(chunks),
                model_used=self.generator.model,
            )

            yield ("done", None)

        except Exception as e:
            logger.exception("Error in query_stream: %s", e)
            yield ("error", str(e))
