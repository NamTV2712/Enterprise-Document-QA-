"""
Module: generator.py
Purpose: Call the Groq API with the retrieved context and return a cited response.
"""

import logging
import re
import time
from dataclasses import dataclass
from threading import Event, Lock
from typing import Any

from src.generation.prompt_contracts import (
    NUMERIC_PAIR_CONTRACT,
    NUMERIC_PAIR_REMINDER,
    answer_completion_contract_for_question,
)
from src.generation.answer_completion import correct_answer_once
from src.generation.period_value_completeness import (
    render_chunk_evidence,
    validate_grounded_answer,
)
from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

GROQ_MAX_RETRIES = 4
GROQ_DEFAULT_RETRY_DELAY_SECONDS = 2.0

SYSTEM_PROMPT = f"""You are a financial analyst assistant. Your job is to answer questions
about SEC 10-K filings accurately and concisely.

STRICT RULES - violation of these rules is worse than saying "I don't know":
1. ONLY use information explicitly stated in the provided context sections below.
   Do NOT use your general knowledge about companies or financial markets.
2. ALWAYS cite the source for every factual claim using the format [Source N].
3. If the context does not contain enough information to answer the question
   confidently, respond EXACTLY with:
   "I could not find sufficient information in the available documents to answer
   this question with confidence."
   Do not list or characterize retrieved sections as relevant in a fallback.
4. Do not speculate, extrapolate, or infer beyond what is explicitly stated.
5. When citing numbers, quote them exactly as they appear in the context.
6. {NUMERIC_PAIR_CONTRACT}
7. When the question does not specify a fiscal year or period, use the most
   recent fiscal year available in the provided context and state that
   fiscal year explicitly in your answer. Never present figures from an
   unstated period.
8. Always respond in English."""

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
    answer_focus = answer_completion_contract_for_question(query)
    focus_line = (
        f"Answer-focus checklist: {answer_focus}\n"
        if answer_focus
        else ""
    )
    return f"""Based on the following context sections from SEC filings, answer the question.
Reference sources as [Source 1], [Source 2], etc.

{context_str}

Question: {query}

{focus_line}Important: if a specific number is not explicitly in the context above, do not state it.
{NUMERIC_PAIR_REMINDER}"""


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
                else [
                    settings.groq_api_key,
                    settings.groq_api_key2,
                    settings.groq_api_key3,
                    settings.groq_api_key4,
                    settings.groq_api_key5,
                ]
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

    def _create_groq_chat_completion(self, **kwargs: Any) -> Any:
        last_stream = None
        for attempt in range(GROQ_MAX_RETRIES + 1):
            client_index, client, wait = self._next_available_client()
            if wait:
                time.sleep(wait)
            try:
                result = client.chat.completions.create(**kwargs)
                # If we got a stream, close any previous failed stream
                if last_stream is not None:
                    close = getattr(last_stream, "close", None)
                    if callable(close):
                        close()
                return result
            except Exception as error:
                # For streaming calls, the result might be a partially-opened stream
                # that needs cleanup before retrying
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

    def _next_available_client(self) -> tuple[int, Any, float]:
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
        response_text = self._apply_answer_completion(
            query, chunks, response_text, conversation_history
        )

        logger.info("Generated response (%d chars) from %s", len(response_text), self.model)
        return RAGResponse(
            answer=response_text,
            retrieved_chunks=chunks,
            model_used=self.model,
        )

    def _apply_answer_completion(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        draft_answer: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Validate and, at most once, correct a scoped answer contract."""
        evidence_context = render_chunk_evidence(chunks)
        outcome = correct_answer_once(
            query,
            evidence_context,
            draft_answer,
            lambda prompt: self._call_groq(prompt, conversation_history),
            validate_answer=lambda answer: validate_grounded_answer(
                answer, evidence_context
            ),
        )
        if outcome.correction_attempted:
            logger.info(
                "Answer completion correction %s for query: %s",
                "accepted" if outcome.correction_accepted else "rejected",
                query[:80],
            )
        return outcome.answer

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

        evidence_context = render_chunk_evidence(chunks)
        from src.generation.answer_completion import (
            assess_answer_completion,
            answer_completion_requires_buffering,
        )

        applicable = answer_completion_requires_buffering(query, evidence_context)
        if not applicable:
            yield from self._call_groq_stream(
                user_message,
                conversation_history,
                cancel_event=cancel_event,
            )
            return

        # An applicable answer must be buffered so an incomplete draft is never
        # emitted before the bounded correction has had a chance to run.
        draft_parts: list[str] = []
        for token in self._call_groq_stream(
            user_message,
            conversation_history,
            cancel_event=cancel_event,
        ):
            if cancel_event is not None and cancel_event.is_set():
                return
            draft_parts.append(token)
        if cancel_event is not None and cancel_event.is_set():
            return

        outcome = correct_answer_once(
            query,
            evidence_context,
            "".join(draft_parts),
            lambda prompt: self._call_groq(prompt, conversation_history),
            validate_answer=lambda answer: validate_grounded_answer(
                answer, evidence_context
            ),
        )
        if outcome.correction_attempted:
            logger.info(
                "Answer completion stream correction %s for query: %s",
                "accepted" if outcome.correction_accepted else "rejected",
                query[:80],
            )
        if cancel_event is None or not cancel_event.is_set():
            yield outcome.answer

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
