"""
Module: rag_pipeline.py
Purpose: The single entry point for the RAG system — connects the Retriever and Generator.
(FastAPI) will only need to import RAGPipeline, nothing else.
"""

import logging
from time import perf_counter
from threading import Event
from uuid import uuid4

from src.generation.execution_trace import ExecutionTrace
from src.generation.visual_answer import build_visual_answer
from src.generation.generator import Generator, RAGResponse
from src.memory.conversation_memory import ConversationMemory, Turn
from src.memory.query_rewriter import QueryRewriter
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_shaper import shape_retrieval_query
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.semantic_cache import CacheEntry, SemanticCache

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        retriever: HybridRetriever,
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
                "document_id": chunk.document_id,
                "filing_type": chunk.filing_type,
                "report_date": chunk.report_date,
                "chunk_index": chunk.chunk_index,
                "source_url": chunk.source_url,
                "score_kind": chunk.score_kind,
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
                document_id=source.get("document_id"),
                filing_type=source.get("filing_type"),
                report_date=source.get("report_date"),
                chunk_index=source.get("chunk_index"),
                source_url=source.get("source_url"),
                score_kind=source.get("score_kind") or "retrieval",
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
                "document_id": chunk.document_id,
                "ticker": chunk.ticker,
                "filing_type": chunk.filing_type,
                "section": chunk.section,
                "filing_date": chunk.filing_date,
                "report_date": chunk.report_date,
                "chunk_index": chunk.chunk_index,
                "source_url": chunk.source_url,
                "score_kind": chunk.score_kind,
                "rank": index + 1,
                "text": chunk.text,
            }
            for index, chunk in enumerate(chunks)
        ]

    def _history_messages(self, session_id: str) -> list[dict]:
        session = self.memory.get_or_create(session_id)
        return session.to_llm_messages()

    def query(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        session_id: str | None = None,
        answer_language: str = "en",
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
        retrieval_query = shape_retrieval_query(effective_query).retrieval_query
        query_embedding = self._embed_query_once(retrieval_query)

        if not session_id:
            cached = self.cache.get(
                query_embedding, ticker, section, top_k, answer_language
            )
            if cached:
                cached_chunks = self._chunks_from_cache(cached)
                return RAGResponse(
                    answer=cached.answer,
                    retrieved_chunks=cached_chunks,
                    model_used=f"{cached.model_used} (cached)",
                    answer_language=answer_language,
                    visual_answer=build_visual_answer(question, cached_chunks),
                )

        chunks = self._retrieve_with_optional_embedding(
            question=retrieval_query,
            query_embedding=query_embedding,
            top_k=top_k,
            ticker=ticker,
            section=section,
        )
        response = self.generator.generate(
            question,
            chunks,
            conversation_history=history_messages,
            answer_language=answer_language,
        )
        response.visual_answer = build_visual_answer(question, chunks)

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
                answer_language=answer_language,
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
        cancel_event: Event | None = None,
        answer_language: str = "en",
        request_id: str | None = None,
    ):
        """Yield SSE-compatible event tuples.

        Cache hits replay sources and answer tokens without calling the LLM.
        Cache misses run retrieval and LLM streaming, then store the full answer.
        """
        try:
            if cancel_event is not None and cancel_event.is_set():
                return

            trace = ExecutionTrace(request_id=request_id or str(uuid4()))
            active_stage: str | None = None
            active_stage_started: float | None = None

            def begin_stage(stage_id: str) -> tuple[str, dict]:
                nonlocal active_stage, active_stage_started
                active_stage = stage_id
                active_stage_started = perf_counter()
                return "stage", trace.stage_event(stage_id, "running")

            def finish_stage(
                stage_id: str,
                started_at: float,
                *,
                trace_status: str = "completed",
                counters: dict[str, int] | None = None,
                metadata: dict[str, str | int | float | bool | None] | None = None,
            ) -> tuple[str, dict]:
                nonlocal active_stage, active_stage_started
                trace.mark(stage_id, started_at, status=trace_status)
                event = trace.stage_event(
                    stage_id,
                    "success",
                    started_at=started_at,
                    counters=counters,
                    metadata=metadata,
                )
                active_stage = None
                active_stage_started = None
                return "stage", event

            history_messages = conversation_history or []
            if session_id:
                self.memory.get_or_create(session_id)
                history_messages = self._history_messages(session_id)

            preparation_started = perf_counter()
            yield begin_stage("query_preparation")
            effective_query = self.rewriter.rewrite(question, history_messages)
            retrieval_query = shape_retrieval_query(effective_query).retrieval_query
            yield finish_stage("query_preparation", preparation_started)
            if cancel_event is not None and cancel_event.is_set():
                return

            embedding_started = perf_counter()
            yield begin_stage("embedding")
            query_embedding = self._embed_query_once(retrieval_query)
            yield finish_stage("embedding", embedding_started)
            if cancel_event is not None and cancel_event.is_set():
                return

            use_cache = not session_id and not history_messages
            if use_cache:
                cache_started = perf_counter()
                yield begin_stage("cache_lookup")
                cached = self.cache.get(
                    query_embedding, ticker, section, top_k, answer_language
                )
                yield finish_stage(
                    "cache_lookup",
                    cache_started,
                    trace_status="hit" if cached else "miss",
                    metadata={"cache": "hit" if cached else "miss"},
                )
                if cached:
                    logger.info("Stream cache HIT for '%s...'", question[:50])
                    yield ("stage", trace.stage_event("retrieval", "skipped", metadata={"reason": "cache_hit"}))
                    yield ("stage", trace.stage_event("generation", "skipped", metadata={"reason": "cache_hit"}))
                    cached_chunks = self._chunks_from_cache(cached)
                    yield ("sources", self._sources_for_stream(cached_chunks))
                    replay_started = perf_counter()
                    yield begin_stage("cache_replay")
                    words = cached.answer.split(" ")
                    for index, word in enumerate(words):
                        if cancel_event is not None and cancel_event.is_set():
                            return
                        token = word if index == len(words) - 1 else f"{word} "
                        yield ("token", token)
                    trace.mark("answer_replay", replay_started, status="cached")
                    yield finish_stage("cache_replay", replay_started, metadata={"cache": "hit"})
                    yield (
                        "done",
                        {
                            "answer_language": answer_language,
                            "request_id": trace.request_id,
                            "request_status": "completed",
                            "execution": trace.payload(),
                            "visual_answer": build_visual_answer(question, cached_chunks),
                        },
                    )
                    return

            retrieval_started = perf_counter()
            yield begin_stage("retrieval")
            chunks = self._retrieve_with_optional_embedding(
                question=retrieval_query,
                query_embedding=query_embedding,
                top_k=top_k,
                ticker=ticker,
                section=section,
            )
            yield finish_stage("retrieval", retrieval_started, counters={"source_count": len(chunks)})
            if cancel_event is not None and cancel_event.is_set():
                return

            sources_data = self._sources_for_stream(chunks)
            yield ("sources", sources_data)

            full_answer = ""
            generation_started = perf_counter()
            yield begin_stage("generation")
            for token in self.generator.generate_stream(
                question,
                chunks,
                conversation_history=history_messages,
                cancel_event=cancel_event,
                answer_language=answer_language,
            ):
                if cancel_event is not None and cancel_event.is_set():
                    return
                full_answer += token
                yield ("token", token)

            yield finish_stage("generation", generation_started)

            if cancel_event is not None and cancel_event.is_set():
                return

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
                    answer_language=answer_language,
                )

            yield (
                "done",
                {
                    "answer_language": answer_language,
                    "request_id": trace.request_id,
                    "request_status": "completed",
                    "execution": trace.payload(),
                    "visual_answer": build_visual_answer(question, chunks),
                },
            )

        except Exception as e:
            logger.exception("Error in query_stream: %s", e)
            if cancel_event is None or not cancel_event.is_set():
                if active_stage and active_stage_started is not None:
                    yield (
                        "stage",
                        trace.stage_event(
                            active_stage,
                            "failed",
                            started_at=active_stage_started,
                            metadata={"reason": "request_failed"},
                        ),
                    )
                yield ("error", "An internal error occurred while processing your question. Please try again.")
