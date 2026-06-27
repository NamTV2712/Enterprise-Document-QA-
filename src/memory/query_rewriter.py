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

logger = logging.getLogger(__name__)

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
        """Rewrite the query when history exists; otherwise return the original."""
        if not history_messages:
            return query

        # Build prompt with history context
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in history_messages[-4:]  # only take the last 2 turns to keep the prompt short
        ])

        prompt = f"""Conversation history:
{history_text}

Follow-up question: {query}

Rewrite the follow-up question as a standalone question:"""

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

            if rewritten and rewritten != query:
                logger.info(
                    "Query rewritten: '%s' -> '%s'", query[:60], rewritten[:60]
                )
            return rewritten or query

        except Exception as e:
            # Rewriter failure should not crash the RAG pipeline.
            logger.warning("Query rewrite failed, using original: %s", e)
            return query
