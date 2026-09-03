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
    _parse_judge_response,
)
from src.evaluation.generation_checkpoint import (
    parse_evidence_context,
    sha256_text,
)
from src.evaluation.judge_checkpoint import JudgeParseErrorStub
from src.generation.generator import SYSTEM_PROMPT, Generator
from src.generation.answer_completion import (
    completion_metadata,
    correct_answer_once,
)
from src.generation.period_value_completeness import (
    correct_period_value_once,
    validate_grounded_answer,
)

logger = logging.getLogger(__name__)

# gpt-oss-120b writes longer completions than the legacy 70B. At a
# 1024-token cap the judge occasionally spent the entire budget on
# reasoning and returned empty content mid-run, so Phase 2 budgets 2048.
# The judge binding includes this cap by design: scores produced under
# different budgets are never mixed.
PHASE2_MAX_TOKENS = 2048
JUDGE_CONTEXT_BUILDER_VERSION = 2
JUDGE_CONTEXT_BUILDER_FINGERPRINT = sha256_text(
    "judge-source-marker-parser-v2-preserve-internal-blank-lines"
)
GENERATION_SYSTEM_PROMPT_FINGERPRINT = sha256_text(SYSTEM_PROMPT)


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
    configured = [
        settings.groq_api_key_fall_back,
        settings.groq_api_key_fall_back2,
    ]
    if not any(configured):
        configured = [settings.groq_api_key, settings.groq_api_key2]
    configured.extend(
        (
            settings.groq_api_key3,
            settings.groq_api_key4,
            settings.groq_api_key5,
        )
    )
    return list(dict.fromkeys(key for key in configured if key))


def judging_pool_keys() -> list[str]:
    """Serving/judging rotation: the primary key pair."""
    return list(
        dict.fromkeys(
            key
            for key in (
                settings.groq_api_key,
                settings.groq_api_key2,
                settings.groq_api_key3,
                settings.groq_api_key4,
                settings.groq_api_key5,
            )
            if key
        )
    )


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


def make_period_value_postprocessor(
    generate_fn: Callable[[str], str],
    metadata: dict[str, dict[str, Any]] | None = None,
) -> Callable[[str, str, str], str]:
    """Apply the shared one-correction policy to a Phase 2 draft."""
    def postprocess(
        question: str,
        evidence_context: str,
        draft_answer: str,
    ) -> str:
        outcome = correct_period_value_once(
            question,
            evidence_context,
            draft_answer,
            generate_fn,
            validate_answer=lambda answer: validate_grounded_answer(
                answer, evidence_context
            ),
        )
        if outcome.correction_attempted:
            logger.info(
                "Phase 2 period/value correction %s for question: %s",
                "accepted" if outcome.correction_accepted else "rejected",
                question[:80],
            )
        if metadata is not None:
            metadata[question] = {
                "applicable": outcome.initial.applicable,
                "initial_passed": outcome.initial.passed,
                "missing_pairs": [
                    {
                        "label": pair.label,
                        "period": pair.period,
                        "value": pair.value,
                        "source_number": pair.source_number,
                    }
                    for pair in outcome.initial.missing_pairs
                ],
                "correction_attempted": outcome.correction_attempted,
                "correction_accepted": outcome.correction_accepted,
                "final_passed": outcome.final.passed,
                "initial_grounding_passed": outcome.initial_grounding_passed,
                "final_grounding_passed": outcome.final_grounding_passed,
                "initial_unsupported_numeric_claims": list(
                    outcome.initial_unsupported_numeric_claims
                ),
                "final_unsupported_numeric_claims": list(
                    outcome.final_unsupported_numeric_claims
                ),
                "correction_reason": outcome.correction_reason,
            }
        return outcome.answer

    return postprocess


def make_answer_completion_postprocessor(
    generate_fn: Callable[[str], str],
    metadata: dict[str, dict[str, Any]] | None = None,
    deterministic_risk_renderer: bool = False,
    deterministic_fact_renderer: bool = False,
    deterministic_revenue_renderer: bool = False,
) -> Callable[[str, str, str], str]:
    """Apply one shared completion policy.

    The deterministic risk renderer is opt-in for candidate evaluation.  The
    default production path continues to use the provider draft plus the
    bounded completion policy.
    """

    def postprocess(
        question: str,
        evidence_context: str,
        draft_answer: str,
    ) -> str:
        outcome = correct_answer_once(
            question,
            evidence_context,
            draft_answer,
            generate_fn,
            validate_answer=lambda answer: validate_grounded_answer(
                answer, evidence_context
            ),
            deterministic_risk_renderer=deterministic_risk_renderer,
            deterministic_fact_renderer=deterministic_fact_renderer,
            deterministic_revenue_renderer=deterministic_revenue_renderer,
        )
        if outcome.correction_attempted:
            logger.info(
                "Phase 2 answer completion %s for question: %s",
                "accepted" if outcome.correction_accepted else "rejected",
                question[:80],
            )
        if metadata is not None:
            metadata[question] = completion_metadata(outcome)
        return outcome.answer

    return postprocess


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
    # Evidence chunks can contain arbitrary blank lines. Splitting on blank
    # lines silently fractures one source into multiple fake chunks and can
    # discard the exact figures the judge needs. Source markers are the only
    # structural boundary in the frozen context format.
    context_blocks = parse_evidence_context(evidence_context)
    context_str = "\n\n".join(
        f"[Chunk {i + 1}] {block['citation']}\n{block['text']}"
        for i, block in enumerate(context_blocks)
    )
    return JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        ground_truth=ground_truth,
        context_str=context_str,
        answer=answer,
    )
