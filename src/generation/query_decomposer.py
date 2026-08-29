"""
Module: query_decomposer.py
Analyze complex queries into independent subqueries,
execute them in parallel, and aggregate the results
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from configs.tickers import TICKERS
from src.generation.comparative_context import (
    ComparativeBranch,
    select_comparative_chunks,
)
from src.generation.prompt_contracts import NUMERIC_PAIR_CONTRACT
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.query_shaper import shape_retrieval_query

logger = logging.getLogger(__name__)


def _is_retryable_external_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "429" in message
        or "rate limit" in message
        or "quota" in message
        or "503" in message
        or "unavailable" in message
    )


SUPPORTED_TICKERS = set(TICKERS)
VALID_SECTIONS = {"business", "risk_factors", "mdna", "financial_statements", "financial_table"}
MIN_CHUNKS_FOR_SYNTHESIS = 2
INSUFFICIENT_DECOMPOSED_CONTEXT_ANSWER = (
    "I could not find sufficient information in the available documents "
    "to answer this question with confidence."
)
SYNTHESIS_ERROR_ANSWER = (
    "I encountered an error while synthesizing the answer from the "
    "retrieved sources. Please try rephrasing your question."
)

DECOMPOSE_SYSTEM_PROMPT = """You are an expert at analyzing financial questions about SEC 10-K filings.
Your job is to determine if a question requires decomposition into sub-queries, and if so, create them.

A question needs decomposition in TWO distinct cases:

CASE 1 - Multi-company comparison: the question compares 2+ companies.
CASE 2 - Single-company enumeration: the question asks to list/enumerate MULTIPLE
distinct items, categories, segments, or topics about ONE company (e.g. "main sources
of revenue", "all risk factors", "product categories", "business segments"). A single
retrieval of top-5 chunks is usually NOT enough to cover all items for these questions,
because each item/category tends to live in a different chunk of the document.

If NEITHER case applies (single fact, single topic, single company), return:
{"needs_decomposition": false}

For CASE 1, return one sub-query per company:
{"needs_decomposition": true, "sub_queries": [
  {"query": "...", "ticker": "AAPL", "section": "..."},
  {"query": "...", "ticker": "MSFT", "section": "..."}
]}

For CASE 2, return 3-5 sub-queries, SAME ticker, each targeting a distinct
filing-native topic/category. Use only concepts named or strongly implied by
the question; do not invent a category list from general knowledge. The final
answer must include only categories actually supported by retrieved excerpts:
{"needs_decomposition": true, "sub_queries": [
  {"query": "specific sub-topic 1", "ticker": "MSFT", "section": "business"},
  {"query": "specific sub-topic 2", "ticker": "MSFT", "section": "business"},
  {"query": "specific sub-topic 3", "ticker": "MSFT", "section": "business"}
]}

Valid section values: business, risk_factors, mdna, financial_statements, financial_table, null
Valid ticker values: use the ticker symbols explicitly named in the question, or null
when the company is unknown.

Examples:
Q: "What are the main sources of revenue for Microsoft?"
A: {"needs_decomposition": true, "sub_queries": [
  {"query": "Microsoft cloud and Azure revenue", "ticker": "MSFT", "section": "business"},
  {"query": "Microsoft Office and productivity software revenue", "ticker": "MSFT", "section": "business"},
  {"query": "Microsoft LinkedIn revenue", "ticker": "MSFT", "section": "business"},
  {"query": "Microsoft gaming and Xbox revenue", "ticker": "MSFT", "section": "business"},
  {"query": "Microsoft Windows and devices revenue", "ticker": "MSFT", "section": "business"}
]}

Q: "What are Apple's main risk factors related to competition?"
A: {"needs_decomposition": false}

Q: "Compare Apple and Microsoft cloud revenue"
A: {"needs_decomposition": true, "sub_queries": [
  {"query": "Apple services and cloud revenue", "ticker": "AAPL", "section": "mdna"},
  {"query": "Microsoft Azure and cloud revenue", "ticker": "MSFT", "section": "mdna"}
]}

Return ONLY valid JSON, no explanation."""

SYNTHESIS_SYSTEM_PROMPT = f"""You are a financial analyst synthesizing information from multiple
SEC 10-K filings to answer a comparative or multi-part question.

Rules:
1. Use ONLY information from the provided context sections.
2. Cite every factual claim with canonical [Source N] markers. Never use
   line-number citations such as 【1†L1-L3】.
3. When comparing companies, structure your answer to make the comparison clear.
4. If information for one company is missing, explicitly state it.
5. Quote numbers exactly as shown in the context, including currency, sign,
   period, and fiscal year. Do not calculate or invent a derived number unless
   the underlying values are explicitly cited.
6. {NUMERIC_PAIR_CONTRACT}
7. Do not add categories or details merely because they are common for the
   company; include only evidence-supported items.
8. If the context is insufficient, say you cannot find sufficient information
   without presenting retrieved sources as relevant.
9. Do not speculate or use external knowledge."""


@dataclass
class SubQuery:
    query: str
    ticker: str | None = None
    section: str | None = None
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)


@dataclass
class DecomposedResponse:
    answer: str
    sub_queries: list[SubQuery]
    all_chunks: list[RetrievedChunk]
    model_used: str
    was_decomposed: bool


def _missing_comparative_tickers(sub_queries: list[SubQuery]) -> set[str]:
    """Return expected company tickers missing from multi-company evidence."""
    expected_tickers = {sq.ticker for sq in sub_queries if sq.ticker is not None}
    if len(expected_tickers) < 2:
        return set()

    evidence_tickers = {
        chunk.ticker
        for sq in sub_queries
        for chunk in sq.retrieved_chunks
    }
    return expected_tickers - evidence_tickers


class QueryDecomposer:
    def __init__(self, pipeline):
        """Receive RAGPipeline to reuse retriever + generator.
        Do not create additional client."""
        self.pipeline = pipeline
        self.generator = pipeline.generator
        self.retriever = pipeline.retriever

    def run(
        self,
        question: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        session_id: str | None = None,
    ) -> DecomposedResponse:
        """Entry point: Decide for yourself whether decomposition is necessary."""
        plan = self._plan(question)

        if not plan.get("needs_decomposition"):
            # Simple query: use the existing pipeline path.
            response = self.pipeline.query(
                question=question,
                top_k=top_k,
                ticker=ticker,
                section=section,
                session_id=session_id,
            )
            return DecomposedResponse(
                answer=response.answer,
                sub_queries=[],
                all_chunks=response.retrieved_chunks,
                model_used=response.model_used,
                was_decomposed=False,
            )

        # Complex query: decompose and execute.
        sub_queries = [
            SubQuery(
                query=sq["query"],
                ticker=sq.get("ticker"),
                section=sq.get("section"),
            )
            for sq in plan.get("sub_queries", [])
        ]

        if not sub_queries:
            logger.warning("Decomposition planned but no sub_queries returned, falling back")
            response = self.pipeline.query(
                question=question,
                top_k=top_k,
                ticker=ticker,
                section=section,
                session_id=session_id,
            )
            return DecomposedResponse(
                answer=response.answer,
                sub_queries=[],
                all_chunks=response.retrieved_chunks,
                model_used=response.model_used,
                was_decomposed=False,
            )

        logger.info(
            "Decomposing '%s...' into %d sub-queries",
            question[:50], len(sub_queries)
        )

        # Execute sub-queries in parallel
        sub_queries = self._execute_parallel(sub_queries, top_k=top_k)

        # Deduplicate and synthesis
        all_chunks = self._deduplicate(sub_queries)
        missing_tickers = _missing_comparative_tickers(sub_queries)
        if len(all_chunks) < MIN_CHUNKS_FOR_SYNTHESIS or missing_tickers:
            logger.warning(
                "Decomposed query has %d unique chunks (minimum %d) and is missing "
                "evidence for tickers %s; returning fallback to avoid hallucination.",
                len(all_chunks),
                MIN_CHUNKS_FOR_SYNTHESIS,
                sorted(missing_tickers),
            )
            return DecomposedResponse(
                answer=INSUFFICIENT_DECOMPOSED_CONTEXT_ANSWER,
                sub_queries=sub_queries,
                all_chunks=all_chunks,
                model_used=self.generator.model,
                was_decomposed=True,
            )

        synthesis_chunks = self._select_comparative_context(
            sub_queries, all_chunks
        )
        answer = self._synthesize(question, synthesis_chunks)

        return DecomposedResponse(
            answer=answer,
            sub_queries=sub_queries,
            all_chunks=synthesis_chunks,
            model_used=self.generator.model,
            was_decomposed=True,
        )

    def _select_comparative_context(
        self,
        sub_queries: list[SubQuery],
        all_chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Pack multi-company evidence with a safe full-context fallback."""
        expected_tickers = {
            sub_query.ticker
            for sub_query in sub_queries
            if sub_query.ticker is not None
        }
        if len(expected_tickers) < 2:
            return all_chunks

        selected = select_comparative_chunks([
            ComparativeBranch(
                query=sub_query.query,
                ticker=sub_query.ticker,
                chunks=sub_query.retrieved_chunks,
            )
            for sub_query in sub_queries
        ])
        selected_tickers = {
            chunk.ticker for chunk in selected if chunk.ticker is not None
        }
        if (
            len(selected) < MIN_CHUNKS_FOR_SYNTHESIS
            or not expected_tickers.issubset(selected_tickers)
        ):
            logger.warning(
                "Comparative context selector would lose evidence: expected=%s "
                "selected=%s; retaining full context (%d chunks)",
                sorted(expected_tickers),
                sorted(selected_tickers),
                len(all_chunks),
            )
            return all_chunks

        logger.info(
            "Comparative context selector reduced synthesis context from %d to %d chunks",
            len(all_chunks),
            len(selected),
        )
        return selected

    def _plan(self, question: str) -> dict:
        """Use LLM to decide whether decomposition is needed and create sub-queries."""
        try:
            raw = self.generator._create_groq_chat_completion(
                model=self.generator.model,
                messages=[
                    {"role": "system", "content": DECOMPOSE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Question: {question}"},
                ],
                max_tokens=700,
                temperature=0,
            ).choices[0].message.content.strip()

            # Strip markdown fences if applicable.
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if match:
                raw = match.group(0)

            plan = self._validate_plan(json.loads(raw))
            logger.info("Decomposition plan (validated): %s", plan)
            return plan

        except Exception as e:
            if _is_retryable_external_error(e):
                raise
            logger.warning("Decomposition planning failed: %s - treating as simple", e)
            return {"needs_decomposition": False}

    def _validate_plan(self, plan: dict) -> dict:
        """Validate LLM-generated structured output before using it.

        Prompt constraints are hints, not contracts. This layer drops invalid
        ticker/section values so out-of-corpus companies do not create wasted
        or misleading sub-query plans.
        """
        if not plan.get("needs_decomposition"):
            return plan

        valid_sub_queries = []
        for sq in plan.get("sub_queries", []):
            ticker = sq.get("ticker")
            section = sq.get("section")

            if ticker is not None and ticker not in SUPPORTED_TICKERS:
                logger.warning(
                    "Planner returned unsupported ticker '%s' for sub-query '%s'; dropping it",
                    ticker,
                    sq.get("query", "")[:50],
                )
                continue

            if section is not None and section not in VALID_SECTIONS:
                logger.warning(
                    "Planner returned unsupported section '%s' for sub-query '%s'; dropping it",
                    section,
                    sq.get("query", "")[:50],
                )
                continue

            valid_sub_queries.append(sq)

        if not valid_sub_queries:
            logger.info("All planned sub-queries were invalid; falling back to simple query")
            return {"needs_decomposition": False}

        return {"needs_decomposition": True, "sub_queries": valid_sub_queries}

    def _execute_parallel(
        self,
        sub_queries: list[SubQuery],
        top_k: int,
    ) -> list[SubQuery]:
        """Retrieve for all sub-queries in parallel.
        ThreadPoolExecutor is suitable because retrieval is I/O-bound
        (Qdrant + cross-encoder inference)."""
        def retrieve_one(sq: SubQuery) -> SubQuery:
            try:
                shaped = shape_retrieval_query(sq.query)
                sq.retrieved_chunks = self.retriever.retrieve(
                    query=shaped.retrieval_query,
                    top_k=top_k,
                    ticker=sq.ticker,
                    section=sq.section,
                )
                logger.info(
                    "Sub-query '%s...' -> %d chunks",
                    shaped.retrieval_query[:60], len(sq.retrieved_chunks)
                )
            except Exception:
                logger.exception(
                    "Sub-query FAILED: '%s' (ticker=%s, section=%s)",
                    sq.query[:40],
                    sq.ticker,
                    sq.section,
                )
                sq.retrieved_chunks = []
            return sq

        with ThreadPoolExecutor(max_workers=min(len(sub_queries), 4)) as executor:
            futures = {executor.submit(retrieve_one, sq): sq for sq in sub_queries}
            results = []
            for future in as_completed(futures):
                results.append(future.result())

        # Rearrange to the original order (as_completed does not guarantee the order)
        order = {id(sq): i for i, sq in enumerate(sub_queries)}
        results.sort(key=lambda sq: order[id(sq)])
        return results

    def _deduplicate(self, sub_queries: list[SubQuery]) -> list[RetrievedChunk]:
        """Combine all chunks and remove duplicates based on chunk_id.
        Keep the chunk with the higher score if the same chunk_id appears
        in multiple sub-queries."""
        seen: dict[str, RetrievedChunk] = {}
        for sq in sub_queries:
            for chunk in sq.retrieved_chunks:
                if chunk.chunk_id not in seen or chunk.score > seen[chunk.chunk_id].score:
                    seen[chunk.chunk_id] = chunk
        return list(seen.values())

    def _synthesize(
        self,
        original_question: str,
        all_chunks: list[RetrievedChunk],
    ) -> str:
        """Generate a synthesized answer from all retrieved chunks."""
        if not all_chunks:
            return (
                "I could not find sufficient information to answer this "
                "comparative question. Please ensure the companies you're "
                "asking about are in the document corpus."
            )

        # Build context with continuous source numbering
        context_parts = []
        for i, chunk in enumerate(all_chunks):
            context_parts.append(
                f"--- Source {i+1} ---\n"
                f"Company: {chunk.ticker} | Section: {chunk.section}\n"
                f"Citation: {chunk.citation}\n"
                f"Content:\n{chunk.text}\n"
            )
        context_str = "\n".join(context_parts)

        user_message = (
            f"Based on the following context from multiple SEC filings, "
            f"answer this question: {original_question}\n\n"
            f"Context:\n{context_str}\n\n"
            f"Provide a clear, comparative answer with citations [Source N]."
        )

        try:
            return self.generator._create_groq_chat_completion(
                model=self.generator.model,
                messages=[
                    {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=1024,
                temperature=0,
            ).choices[0].message.content
        except Exception as error:
            if _is_retryable_external_error(error):
                raise
            logger.exception(
                "Synthesis failed for question: %s (chunks=%d)",
                original_question[:80],
                len(all_chunks),
            )
            return SYNTHESIS_ERROR_ANSWER
