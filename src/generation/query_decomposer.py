"""
Module: query_decomposer.py
Analyze complex queries into independent subqueries,
execute them in parallel, and aggregate the results
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

SUPPORTED_TICKERS = ["AAPL", "MSFT", "AMZN"]  # will read from config after expanding corpus

DECOMPOSE_SYSTEM_PROMPT = """You are an expert at analyzing financial questions about SEC 10-K filings.
Your job is to determine if a question requires information from multiple companies or multiple topics,
and if so, break it into simple sub-queries.

Rules:
1. If the question can be answered from ONE company's ONE section, return:
   {"needs_decomposition": false}

2. If the question requires comparing multiple companies OR combining multiple topics, return:
   {"needs_decomposition": true, "sub_queries": [
     {"query": "specific question 1", "ticker": "AAPL or null", "section": "section_name or null"},
     {"query": "specific question 2", "ticker": "MSFT or null", "section": "section_name or null"}
   ]}

Valid section values: business, risk_factors, mdna, financial_statements, null (search all)
Valid ticker values: AAPL, MSFT, AMZN, null (search all)

Return ONLY valid JSON, no explanation."""

SYNTHESIS_SYSTEM_PROMPT = """You are a financial analyst synthesizing information from multiple 
SEC 10-K filings to answer a comparative or multi-part question.

Rules:
1. Use ONLY information from the provided context sections.
2. Clearly attribute information to the correct company using [Source N].
3. When comparing companies, structure your answer to make the comparison clear.
4. If information for one company is missing, explicitly state it.
5. Do not speculate or use external knowledge."""


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
        session_id: str | None = None,
    ) -> DecomposedResponse:
        """Entry point: Decide for yourself whether decomposition is necessary."""
        plan = self._plan(question)

        if not plan.get("needs_decomposition"):
            # Simple query: use the existing pipeline path.
            response = self.pipeline.query(
                question=question,
                top_k=top_k,
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
        answer = self._synthesize(question, all_chunks)

        return DecomposedResponse(
            answer=answer,
            sub_queries=sub_queries,
            all_chunks=all_chunks,
            model_used=self.generator.model,
            was_decomposed=True,
        )

    def _plan(self, question: str) -> dict:
        """Use LLM to decide whether decomposition is needed and create sub-queries."""
        try:
            if self.generator.provider == "groq":
                raw = self.generator.client.chat.completions.create(
                    model=self.generator.model,
                    messages=[
                        {"role": "system", "content": DECOMPOSE_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Question: {question}"},
                    ],
                    max_tokens=300,
                    temperature=0,
                ).choices[0].message.content.strip()
            else:
                from google.genai import types
                raw = self.generator.client.models.generate_content(
                    model=self.generator.model,
                    config=types.GenerateContentConfig(
                        system_instruction=DECOMPOSE_SYSTEM_PROMPT,
                        max_output_tokens=300,
                    ),
                    contents=f"Question: {question}",
                ).text.strip()

            # Strip markdown fences if applicable.
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            plan = json.loads(raw)
            logger.info("Decomposition plan: %s", plan)
            return plan

        except Exception as e:
            logger.warning("Decomposition planning failed: %s - treating as simple", e)
            return {"needs_decomposition": False}

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
                sq.retrieved_chunks = self.retriever.retrieve(
                    query=sq.query,
                    top_k=top_k,
                    ticker=sq.ticker,
                    section=sq.section,
                )
                logger.info(
                    "Sub-query '%s...' -> %d chunks",
                    sq.query[:40], len(sq.retrieved_chunks)
                )
            except Exception as e:
                logger.error("Sub-query failed '%s': %s", sq.query[:40], e)
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
            if self.generator.provider == "groq":
                return self.generator.client.chat.completions.create(
                    model=self.generator.model,
                    messages=[
                        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=1024,
                    temperature=0,
                ).choices[0].message.content
            else:
                from google.genai import types
                return self.generator.client.models.generate_content(
                    model=self.generator.model,
                    config=types.GenerateContentConfig(
                        system_instruction=SYNTHESIS_SYSTEM_PROMPT,
                        max_output_tokens=1024,
                    ),
                    contents=user_message,
                ).text
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            return f"Error synthesizing answer: {e}"
