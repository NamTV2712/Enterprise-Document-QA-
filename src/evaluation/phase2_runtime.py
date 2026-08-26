"""Shared Phase 2 provider-call plumbing for probe and official runners.

Both ``scripts/run_quota_probe.py`` and ``scripts/run_evaluation_phase2.py``
must issue generation and judging calls under identical conditions; keeping
the factories here prevents the quota probe and the official N=30 run from
drifting apart. Retrieval never runs in this module: Phase 2 consumers work
only from the frozen Phase 1 artifact evidence.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from configs.settings import settings
from src.evaluation.evaluator import (
    JUDGE_PROMPT_TEMPLATE,
    JUDGE_SYSTEM_PROMPT,
    JudgeParseError,
    _extract_relevant_window,
    _parse_judge_response,
)
from src.evaluation.judge_checkpoint import JudgeParseErrorStub
from src.generation.generator import SYSTEM_PROMPT, Generator

logger = logging.getLogger(__name__)

# gpt-oss-120b writes longer completions than the legacy 70B; the old
# 320-token cap truncated judge JSON mid-object during the first probe.
PHASE2_MAX_TOKENS = 1024


class UsageTracker:
    """Aggregate prompt/completion tokens per phase for run summaries."""

    def __init__(self) -> None:
        self.totals: dict[str, int] = {
            "generation_prompt_tokens": 0,
            "generation_completion_tokens": 0,
            "judging_prompt_tokens": 0,
            "judging_completion_tokens": 0,
        }

    def record(self, phase: str, usage: Any, elapsed: float) -> None:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        if prompt_tokens is not None:
            self.totals[f"{phase}_prompt_tokens"] += int(prompt_tokens)
        if completion_tokens is not None:
            self.totals[f"{phase}_completion_tokens"] += int(completion_tokens)
        logger.info(
            "%s call done in %.2fs (prompt=%s, completion=%s tokens)",
            phase,
            elapsed,
            prompt_tokens,
            completion_tokens,
        )


def generation_pool_keys() -> list[str]:
    """Evaluation-generation rotation: dedicated pair, then primary."""
    keys = [settings.groq_api_key_fall_back, settings.groq_api_key_fall_back2]
    if not any(keys):
        keys = [settings.groq_api_key, settings.groq_api_key2]
    return keys


def judging_pool_keys() -> list[str]:
    """Serving/judging rotation: the primary key pair."""
    return [settings.groq_api_key, settings.groq_api_key2]


def make_generation_call(
    generator: Generator, tracker: UsageTracker
) -> Callable[[str], str]:
    def generate(prompt: str) -> str:
        started = time.perf_counter()
        response = generator._create_groq_chat_completion(
            model=generator.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=PHASE2_MAX_TOKENS,
            temperature=0,
        )
        elapsed = time.perf_counter() - started
        tracker.record("generation", getattr(response, "usage", None), elapsed)
        return response.choices[0].message.content or ""

    return generate


def make_judge_call(
    generator: Generator, tracker: UsageTracker
) -> Callable[[str], dict]:
    def judge(prompt: str) -> dict:
        started = time.perf_counter()
        response = generator._create_groq_chat_completion(
            model=generator.model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=PHASE2_MAX_TOKENS,
            temperature=0,
        )
        elapsed = time.perf_counter() - started
        tracker.record("judging", getattr(response, "usage", None), elapsed)
        raw = response.choices[0].message.content or ""
        try:
            return _parse_judge_response(raw)
        except JudgeParseError as parse_error:
            raise JudgeParseErrorStub(str(parse_error)) from parse_error

    return judge


def build_production_judge_prompt(
    question: str, answer: str, evidence_context: str, ground_truth: str
) -> str:
    """Production judging instructions over the frozen evidence blocks."""
    context_texts = [
        block.split("\n", 1)[1]
        for block in evidence_context.split("\n\n")
        if "\n" in block
    ]
    context_str = "\n\n".join(
        f"[Chunk {i+1}]: {_extract_relevant_window(text, question)}"
        for i, text in enumerate(context_texts)
    )
    return JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        ground_truth=ground_truth,
        context_str=context_str,
        answer=answer,
    )
