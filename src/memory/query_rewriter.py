"""
Module: query_rewriter.py
Rewrite follow-up questions as standalone queries.
This is the most important step of multi-turn RAG that
most tutorials skip.

Example:
History: Q: "Apple risk factors?" A: "Competition, supply chain..."
User: "What about their revenue?"
Rewritten: "What is Apple's total revenue?"
"""

import logging
import re

logger = logging.getLogger(__name__)
YEAR_PATTERN = re.compile(r"\b20\d{2}\b")
TREND_KEYWORDS = (
    "growth",
    "trend",
    "change",
    "changed",
    "year over year",
    "year-over-year",
    "yoy",
)
ASSET_TREND_STOPWORDS = {
    "how",
    "did",
    "does",
    "do",
    "what",
    "was",
    "were",
    "is",
    "are",
    "the",
    "a",
    "an",
    "change",
    "changed",
    "growth",
    "trend",
    "year",
    "over",
    "yoy",
}

REWRITE_SYSTEM_PROMPT = """You are a query rewriting assistant for a financial document QA system.
Your job is to rewrite a follow-up question into a standalone question that can be 
understood without the conversation history.

Rules:
1. If the question is already standalone (no pronouns referring to previous context,
   no "also", "too", "as well", "what about"), return it UNCHANGED.
2. Replace pronouns (they, their, it, its, the company, the firm) with the actual 
   entity name from conversation history.
3. Add relevant context (company name, year, topic) from history if needed.
4. For revenue follow-ups, rewrite toward total revenue or total net sales,
   not revenue recognition policy.
5. Keep the rewritten question concise: one sentence maximum.
6. Return ONLY the rewritten question, no explanation, no quotes."""


class QueryRewriter:
    """Rewrite follow-up queries as standalone queries using LLM.

    Only called when there is conversation history, avoiding unnecessary API calls
    for the first question in a session.
    """

    def __init__(self, generator):
        # Reuse the existing generator; do not create new clients
        self._generator = generator

    def rewrite(self, query: str, history_messages: list[dict]) -> str:
        """Rewrite follow-ups and underspecified trend queries for retrieval."""
        needs_trend_expansion = self._needs_trend_expansion(query)
        if not history_messages and not needs_trend_expansion:
            return query
        if not history_messages and needs_trend_expansion and "asset" in query.lower():
            return self._build_asset_table_query(query)

        prompt = self._build_prompt(query, history_messages, needs_trend_expansion)

        try:
            if self._generator.provider == "groq":
                rewritten = self._generator.client.chat.completions.create(
                    model=self._generator.model,
                    messages=[
                        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=100,
                    temperature=0,
                ).choices[0].message.content.strip()
            else:
                # Gemini fallback.
                from google.genai import types
                rewritten = self._generator.client.models.generate_content(
                    model=self._generator.model,
                    config=types.GenerateContentConfig(
                        system_instruction=REWRITE_SYSTEM_PROMPT,
                        max_output_tokens=100,
                    ),
                    contents=prompt,
                ).text.strip()

            if needs_trend_expansion:
                rewritten = self._append_table_hints(query, rewritten or query)

            if rewritten and rewritten != query:
                logger.info(
                    "Query rewritten: '%s' -> '%s'", query[:60], rewritten[:60]
                )
            return rewritten or query

        except Exception as e:
            # Rewriter failure should not crash the RAG pipeline.
            logger.warning("Query rewrite failed, using original: %s", e)
            return query

    @staticmethod
    def _needs_trend_expansion(query: str) -> bool:
        normalized = query.lower()
        return any(keyword in normalized for keyword in TREND_KEYWORDS) and not YEAR_PATTERN.search(query)

    @staticmethod
    def _build_prompt(
        query: str,
        history_messages: list[dict],
        needs_trend_expansion: bool,
    ) -> str:
        if history_messages:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in history_messages[-4:]  # only take the last 2 turns to keep the prompt short
            ])
            return f"""Conversation history:
{history_text}

Follow-up question: {query}

Rewrite the follow-up question as a standalone question:"""

        if needs_trend_expansion:
            return f"""Question: {query}

Rewrite this financial trend/growth question for retrieval over SEC 10-K tables.
Keep the original company and metric. Add the latest fiscal years 2025, 2024, and 2023 if they are not already present.
Use concrete table-friendly terms such as net sales, revenue, total assets, increase, decrease, and year-over-year when relevant.
Return one concise standalone retrieval query:"""

        return query

    @staticmethod
    def _append_table_hints(original_query: str, rewritten_query: str) -> str:
        normalized = original_query.lower()
        hints = []
        if "asset" in normalized:
            hints.append("balance sheets Assets - Total assets total current assets")
        if "revenue" in normalized or "sales" in normalized:
            hints.append("net sales revenue")
        if "aws" in normalized:
            hints.append("AWS net sales")

        if not hints:
            return rewritten_query
        return f"{rewritten_query} {' '.join(hints)}"

    @staticmethod
    def _build_asset_table_query(query: str) -> str:
        normalized = query.replace("'s", "").replace("’s", "")
        tokens = re.findall(r"[A-Za-z0-9-]+", normalized)
        core_terms = [
            token
            for token in tokens
            if token.lower() not in ASSET_TREND_STOPWORDS
        ]
        return (
            f"{' '.join(core_terms)} balance sheets Assets - Total assets "
            "total current assets 2025 2024 2023"
        )
