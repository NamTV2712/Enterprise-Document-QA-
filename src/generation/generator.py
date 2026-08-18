"""
Module: generator.py
Purpose: Call the Groq API with the retrieved context and return a cited response.
"""

import logging
import re
import time
from dataclasses import dataclass
from threading import Event, Lock

from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

GROQ_MAX_RETRIES = 4
GROQ_DEFAULT_RETRY_DELAY_SECONDS = 2.0

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

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
    ):
        from configs.settings import settings
        from groq import Groq

        configured_keys = (
            api_keys
            if api_keys is not None
            else (
                [api_key]
                if api_key
                else [settings.groq_api_key, settings.groq_api_key2]
            )
        )
        selected_keys = list(dict.fromkeys(key for key in configured_keys if key))
        if not selected_keys:
            raise ValueError("GROQ_API_KEY is not configured in .env")
        self.clients = [Groq(api_key=key) for key in selected_keys]
        # Preserve the old public attribute for integrations that inspect it.
        self.client = self.clients[0]
        self._client_cursor = 0
        self._client_cooldowns = [0.0] * len(self.clients)
        self._client_lock = Lock()
        self.model = model or "openai/gpt-oss-120b"

    @staticmethod
    def _groq_retry_delay(error: Exception) -> float | None:
        message = str(error).lower()
        if "429" not in message and "rate limit" not in message:
            return None

        match = re.search(r"try again in ([0-9.]+)\s*(ms|s)", message)
        if not match:
            return GROQ_DEFAULT_RETRY_DELAY_SECONDS

        value = float(match.group(1))
        unit = match.group(2)
        delay = value / 1000 if unit == "ms" else value
        return min(delay + 0.5, 30.0)

    def _create_groq_chat_completion(self, **kwargs):
        for attempt in range(GROQ_MAX_RETRIES + 1):
            client_index, client, wait = self._next_available_client()
            if wait:
                time.sleep(wait)
            try:
                return client.chat.completions.create(**kwargs)
            except Exception as error:
                delay = self._groq_retry_delay(error)
                if delay is None or attempt >= GROQ_MAX_RETRIES:
                    raise
                self._cool_down_client(client_index, delay)
                logger.warning(
                    "Groq key %d/%d rate-limited; rotating key (attempt %d/%d)",
                    client_index + 1,
                    len(self.clients),
                    attempt + 1,
                    GROQ_MAX_RETRIES,
                )

    def _next_available_client(self) -> tuple[int, object, float]:
        """Select a ready key round-robin, or return the shortest cooldown."""
        # Keep lightweight test doubles and older integrations that assign only
        # ``client`` compatible with the pooled implementation.
        if not hasattr(self, "clients"):
            self.clients = [self.client]
            self._client_cursor = 0
            self._client_cooldowns = [0.0]
        if not hasattr(self, "_client_lock"):
            self._client_lock = Lock()
        with self._client_lock:
            now = time.monotonic()
            for offset in range(len(self.clients)):
                index = (self._client_cursor + offset) % len(self.clients)
                if self._client_cooldowns[index] <= now:
                    self._client_cursor = (index + 1) % len(self.clients)
                    return index, self.clients[index], 0.0

            index = min(
                range(len(self.clients)),
                key=self._client_cooldowns.__getitem__,
            )
            wait = max(0.0, self._client_cooldowns[index] - now)
            self._client_cursor = (index + 1) % len(self.clients)
            return index, self.clients[index], wait

    def _cool_down_client(self, client_index: int, delay: float) -> None:
        with self._client_lock:
            self._client_cooldowns[client_index] = max(
                self._client_cooldowns[client_index],
                time.monotonic() + delay,
            )

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

        response_text = self._call_groq(user_message, conversation_history)

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

        response = self._create_groq_chat_completion(
            model=self.model,
            messages=messages,
            max_tokens=1024,
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def generate_stream(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        conversation_history: list[dict] | None = None,
        cancel_event: Event | None = None,
    ):
        """Yield each token received from the LLM."""
        if cancel_event is not None and cancel_event.is_set():
            return

        if not chunks:
            yield "I could not find any relevant information in the available documents"
            return

        best_score = max(c.score for c in chunks)
        if best_score < self.LOW_SCORE_THRESHOLD:
            logger.warning(
                "Best score %.4f < threshold — The context may be irrelevant", best_score
            )

        user_message = _build_user_message(query, chunks)

        yield from self._call_groq_stream(
            user_message,
            conversation_history,
            cancel_event=cancel_event,
        )

    def _call_groq_stream(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        cancel_event: Event | None = None,
    ):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        stream = self._create_groq_chat_completion(
            model=self.model,
            messages=messages,
            max_tokens=1024,
            temperature=0,
            stream=True,
        )
        try:
            for chunk in stream:
                if cancel_event is not None and cancel_event.is_set():
                    break
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()
