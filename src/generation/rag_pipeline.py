"""
Module: rag_pipeline.py
Purpose: The single entry point for the RAG system — connects the Retriever and Generator.
(FastAPI) will only need to import RAGPipeline, nothing else.
"""

import logging

from src.generation.generator import Generator, RAGResponse
from src.memory.conversation_memory import ConversationMemory, Turn
from src.memory.query_rewriter import QueryRewriter
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
        memory: ConversationMemory | None = None,
    ):
        self.retriever = retriever
        self.generator = generator
        self.cache = cache or SemanticCache()
        self.memory = memory or ConversationMemory()
        self.rewriter = QueryRewriter(generator)

    def _embed_query_once(self, question: str) -> list[float]:
        if hasattr(self.retriever, "embed_query"):
            return self.retriever.embed_query(question)
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

    def _history_messages(self, session_id: str) -> list[dict]:
        messages = []
        for turn in self.memory.get_history(session_id):
            messages.append({"role": "user", "content": turn.user_message})
            messages.append({"role": "assistant", "content": turn.assistant_message})
        return messages

    def query(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        session_id: str | None = None,
    ) -> RAGResponse:
        logger.info(
            "RAG query: '%s...' (ticker=%s, section=%s, session=%s)",
            question[:50],
            ticker,
            section,
            session_id,
        )

        history_messages = []
        if session_id:
            self.memory.get_or_create(session_id)
            history_messages = self._history_messages(session_id)

        effective_query = self.rewriter.rewrite(question, history_messages)
        query_embedding = self._embed_query_once(effective_query)

        if not session_id:
            cached = self.cache.get(query_embedding, ticker, section, top_k)
            if cached:
                return RAGResponse(
                    answer=cached.answer,
                    retrieved_chunks=self._chunks_from_cache(cached),
                    model_used=f"{cached.model_used} (cached)",
                )

        chunks = self._retrieve_with_optional_embedding(
            question=effective_query,
            query_embedding=query_embedding,
            top_k=top_k,
            ticker=ticker,
            section=section,
        )
        response = self.generator.generate(
            question,
            chunks,
            conversation_history=history_messages,
        )

        if session_id:
            self.memory.add_turn(
                session_id,
                Turn(
                    user_message=question,
                    assistant_message=response.answer,
                    rewritten_query=effective_query if effective_query != question else None,
                ),
            )
        else:
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
        session_id: str | None = None,
    ):
        """Yield SSE-compatible event tuples.

        Cache hits replay sources and answer tokens without calling the LLM.
        Cache misses run retrieval and LLM streaming, then store the full answer.
        """
        try:
            history_messages = conversation_history or []
            if session_id:
                self.memory.get_or_create(session_id)
                history_messages = self._history_messages(session_id)

            effective_query = self.rewriter.rewrite(question, history_messages)
            query_embedding = self._embed_query_once(effective_query)

            use_cache = not session_id and not history_messages
            if use_cache:
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
                question=effective_query,
                query_embedding=query_embedding,
                top_k=top_k,
                ticker=ticker,
                section=section,
            )

            sources_data = self._sources_for_stream(chunks)
            yield ("sources", sources_data)

            full_answer = ""
            for token in self.generator.generate_stream(
                question,
                chunks,
                conversation_history=history_messages,
            ):
                full_answer += token
                yield ("token", token)

            if session_id:
                self.memory.add_turn(
                    session_id,
                    Turn(
                        user_message=question,
                        assistant_message=full_answer,
                        rewritten_query=effective_query if effective_query != question else None,
                    ),
                )
            elif use_cache:
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
