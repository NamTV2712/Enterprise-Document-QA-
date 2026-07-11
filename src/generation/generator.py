"""
Module: generator.py
Purpose: Call the LLM API with the retrieved context and return a cited response.
Supports Groq and Gemini — select via config.
"""

import logging
from dataclasses import dataclass

from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial analyst assistant. Your job is to answer questions
about SEC 10-K filings accurately and concisely.

STRICT RULES - violation of these rules is worse than saying "I don't know":
1. ONLY use information explicitly stated in the provided context sections below.
   Do NOT use your general knowledge about companies or financial markets.
2. ALWAYS cite the source for every factual claim using the format [Source N].
3. If the context does not contain enough information to answer the question
   confidently, respond EXACTLY with:
   "I could not find sufficient information in the available documents to answer
   this question with confidence. The most relevant sections I found were: [list sources]."
4. Do not speculate, extrapolate, or infer beyond what is explicitly stated.
5. When citing numbers, quote them exactly as they appear in the context.
6. When the context contains specific numeric figures relevant to a trend,
   comparison, or growth question, always quote the exact underlying values
   for each year or period mentioned, in addition to any percentage or
   qualitative description. A percentage alone is not sufficient when specific
   numbers are available in the context.
7. Always respond in English."""

CONTEXT_TEMPLATE = """--- Context Section {index} ---
Source: {citation}
Content:
{text}
"""


@dataclass
class RAGResponse:
    answer: str
    retrieved_chunks: list[RetrievedChunk]
    model_used: str


def _format_context(chunks: list[RetrievedChunk]) -> str:
    return "\n".join(
        CONTEXT_TEMPLATE.format(
            index=i + 1,
            citation=chunk.citation,
            text=chunk.text,
        )
        for i, chunk in enumerate(chunks)
    )


def _build_user_message(query: str, chunks: list[RetrievedChunk]) -> str:
    context_str = _format_context(chunks)
    return f"""Based on the following context sections from SEC filings, answer the question.
Reference sources as [Source 1], [Source 2], etc.

{context_str}

Question: {query}

Important: if a specific number is not explicitly in the context above, do not state it."""


class Generator:
    """Wrapper LLM — only handles API calls and response formatting.
        Knows nothing about retrieval or vector DB."""

    LOW_SCORE_THRESHOLD = 0.50
    # If the best chunk has a score below this threshold, the context may not be
    # relevant enough. Log it instead of silently producing a weak answer.

    def __init__(self, provider: str = "groq", model: str | None = None):
        self.provider = provider
        from configs.settings import settings

        if provider == "groq":
            from groq import Groq
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY is not configured in .env")
            self.client = Groq(api_key=settings.groq_api_key)
            self.model = model or "llama-3.3-70b-versatile"
        elif provider == "gemini":
            from google import genai
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not configured in .env")
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.model = model or "gemini-2.5-flash-lite"
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'groq' or 'gemini'.")

    def generate(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        conversation_history: list[dict] | None = None,
    ) -> RAGResponse:
        if not chunks:
            return RAGResponse(
                answer="I could not find any relevant information in the available documents.",
                retrieved_chunks=[],
                model_used=self.model,
            )

        # Check retrieval quality before spending an LLM call.
        best_score = max(c.score for c in chunks)
        if best_score < self.LOW_SCORE_THRESHOLD:
            logger.warning(
                "Best retrieval score %.4f < threshold %.2f - context may not be relevant enough.",
                best_score, self.LOW_SCORE_THRESHOLD
            )

        user_message = _build_user_message(query, chunks)

        if self.provider == "groq":
            response_text = self._call_groq(user_message, conversation_history)
        elif self.provider == "gemini":
            response_text = self._call_gemini(user_message, conversation_history)

        logger.info("Generated response (%d chars) from %s", len(response_text), self.model)
        return RAGResponse(
            answer=response_text,
            retrieved_chunks=chunks,
            model_used=self.model,
        )

    def _call_groq(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def _call_gemini(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        from google.genai import types

        if conversation_history:
            history_text = "\n".join(
                f"{message['role'].upper()}: {message['content']}"
                for message in conversation_history
            )
            user_message = f"""Conversation history:
{history_text}

Current request:
{user_message}"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1024,
                temperature=0,
            ),
        )
        return response.text or ""

    def generate_stream(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        conversation_history: list[dict] | None = None,
    ):
        """Yield each token received from the LLM."""
        if not chunks:
            yield "I could not find any relevant information in the available documents"
            return

        best_score = max(c.score for c in chunks)
        if best_score < self.LOW_SCORE_THRESHOLD:
            logger.warning(
                "Best score %.4f < threshold — The context may be irrelevant", best_score
            )

        user_message = _build_user_message(query, chunks)

        if self.provider == "groq":
            yield from self._call_groq_stream(user_message, conversation_history)
        elif self.provider == "gemini":
            yield from self._call_gemini_stream(user_message, conversation_history)
        else:
            raise ValueError(f"Provider '{self.provider}' does not support streaming.")

    def _call_groq_stream(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
            temperature=0,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def _call_gemini_stream(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ):
        from google.genai import types
        if conversation_history:
            history_text = "\n".join(
                f"{message['role'].upper()}: {message['content']}"
                for message in conversation_history
            )
            user_message = f"""Conversation history:
{history_text}

Current request:
{user_message}"""

        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1024,
            ),
            contents=user_message,
        ):
            if chunk.text:
                yield chunk.text
