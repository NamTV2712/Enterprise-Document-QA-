"""One bounded, evidence-only completion pass for generated answers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from src.generation.enumeration_completeness import (
    EnumerationCompleteness,
    assess_enumeration_completeness,
    append_missing_enumeration_items,
    compact_enumeration_answer,
)
from src.generation.period_value_completeness import (
    FALLBACK_ANSWER,
    GroundedCompletionAssessment,
    PeriodValueCorrectionError,
    assess_grounded_completion,
    build_period_value_correction_prompt,
    parse_evidence_sources,
    validate_grounded_answer,
)


ANSWER_COMPLETION_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"answer-completion-v1-generic-enumeration-boundary-revenue-granularity-scoped-bullet-compaction-grouped-home-alias-evidence-label-repair-revenue-top-level-dedup-generic-numeric-grounding-repair-period-value-one-correction"
).hexdigest()


class AnswerCompletionError(PeriodValueCorrectionError):
    """Provider failure while attempting the single bounded correction."""


@dataclass(frozen=True)
class AnswerCompletionAssessment:
    """Combined deterministic assessment before or after correction."""

    period_value: GroundedCompletionAssessment
    enumeration: EnumerationCompleteness
    grounding_passed: bool
    unsupported_numeric_claims: tuple[str, ...]
    correction_required: bool


@dataclass(frozen=True)
class AnswerCompletion:
    """Result and audit metadata for one answer-completion decision."""

    answer: str
    initial: AnswerCompletionAssessment
    final: AnswerCompletionAssessment
    correction_attempted: bool
    correction_accepted: bool
    correction_reason: str = ""
    answer_compacted: bool = False


def _answer_contract_audit(
    answer: str, evidence_context: str
) -> tuple[bool, tuple[str, ...]]:
    from src.evaluation.answer_contract import audit_answer

    source_texts = [
        source.text for source in parse_evidence_sources(evidence_context)
    ]
    audit = audit_answer(answer, source_texts)
    passed = (
        bool(audit.canonical_citations)
        and not audit.fallback_answer
        and not audit.uncited_answer
        and not audit.out_of_range_citations
        and not audit.unsupported_numeric_claims
    )
    return passed, tuple(audit.unsupported_numeric_claims)


def assess_answer_completion(
    question: str,
    evidence_context: str,
    answer: str,
) -> AnswerCompletionAssessment:
    """Assess only the scoped contract relevant to this question."""
    period_value = assess_grounded_completion(
        question, evidence_context, answer
    )
    enumeration = assess_enumeration_completeness(
        question, evidence_context, answer
    )
    if enumeration.applicable:
        grounding_passed, unsupported_numeric_claims = _answer_contract_audit(
            answer, evidence_context
        )
        correction_required = (
            not enumeration.passed or not grounding_passed
        )
    elif period_value.period_value.applicable:
        grounding_passed = period_value.grounding_passed
        unsupported_numeric_claims = period_value.unsupported_numeric_claims
        correction_required = period_value.correction_required
    else:
        # Keep the unified postprocessor lightweight for ordinary qualitative
        # answers, but do not let an unsupported numeric claim bypass the
        # shared grounding contract merely because the conservative
        # period/value detector did not classify the question as numeric.
        grounding_passed, unsupported_numeric_claims = _answer_contract_audit(
            answer, evidence_context
        )
        correction_required = bool(unsupported_numeric_claims)
    return AnswerCompletionAssessment(
        period_value,
        enumeration,
        grounding_passed,
        unsupported_numeric_claims,
        correction_required,
    )


def _build_correction_prompt(
    question: str,
    evidence_context: str,
    draft_answer: str,
    assessment: AnswerCompletionAssessment,
) -> str:
    sections: list[str] = []
    if assessment.period_value.period_value.applicable:
        period_prompt = build_period_value_correction_prompt(
            question,
            evidence_context,
            draft_answer,
            assessment.period_value.period_value,
            assessment.period_value.unsupported_numeric_claims,
        )
        sections.append(period_prompt.split("\n\nQuestion:", 1)[0])
    if assessment.enumeration.applicable and assessment.enumeration.missing_items:
        missing = "\n".join(
            f"- Source {item.source_number}: {item.label}"
            for item in assessment.enumeration.missing_items
        )
        sections.append(
            "The draft omitted these explicit evidence-backed enumeration "
            f"items:\n{missing}"
        )
    if assessment.enumeration.applicable and assessment.enumeration.overdetailed:
        sections.append(
            "The draft is over-detailed for the requested enumeration. Keep "
            "one concise bullet per evidence item and remove examples, "
            "sub-products, features, and sub-risks that are not separate "
            "evidence items."
        )
    if (
        assessment.enumeration.applicable
        and assessment.enumeration.ambiguous_items
    ):
        sections.append(
            "Enumeration evidence was insufficient or ambiguous; do not add "
            "unsupported categories."
        )
    if assessment.unsupported_numeric_claims:
        sections.append(
            "Remove numeric claims not printed in the cited evidence: "
            + ", ".join(assessment.unsupported_numeric_claims)
        )
    details = "\n\n".join(sections)
    return (
        "Correct the draft using only the same SEC evidence below. Return one "
        "concise final answer only. Preserve canonical [Source N] citations, "
        "include every explicit evidence-backed enumeration item exactly once, "
        "and do not add items from general knowledge. Quote values exactly as "
        "printed; do not calculate, round, convert, or invent values.\n\n"
        f"{details}\n\nQuestion: {question}\n\nEvidence:\n"
        f"{evidence_context}\n\nDraft answer:\n{draft_answer}"
    )


def correct_answer_once(
    question: str,
    evidence_context: str,
    draft_answer: str,
    generate_fn: Callable[[str], str],
    validate_answer: Callable[[str], bool] | None = None,
) -> AnswerCompletion:
    """Apply at most one provider correction for the scoped contracts."""
    initial = assess_answer_completion(question, evidence_context, draft_answer)
    if not initial.correction_required:
        answer, compacted = compact_enumeration_answer(
            draft_answer, initial.enumeration
        )
        final = (
            assess_answer_completion(question, evidence_context, answer)
            if compacted
            else initial
        )
        return AnswerCompletion(
            answer,
            initial,
            final,
            False,
            False,
            "",
            compacted,
        )

    reasons: list[str] = []
    if initial.period_value.period_value.applicable and not (
        initial.period_value.period_value.passed
    ):
        reasons.append("missing_period_value_pairs")
    if initial.enumeration.applicable and not initial.enumeration.passed:
        reasons.append(
            "overdetailed_enumeration"
            if initial.enumeration.overdetailed
            else "missing_enumeration_items"
        )
    if not initial.grounding_passed:
        reasons.append("grounding_violation")
    try:
        corrected = generate_fn(
            _build_correction_prompt(
                question, evidence_context, draft_answer, initial
            )
        )
    except Exception as error:
        raise AnswerCompletionError(str(error)) from error

    corrected_assessment = assess_answer_completion(
        question, evidence_context, corrected
    )
    answer, compacted = compact_enumeration_answer(
        corrected, corrected_assessment.enumeration
    )
    final = assess_answer_completion(question, evidence_context, answer)
    if final.enumeration.applicable and final.enumeration.missing_items:
        # Only repair a still-grounded provider answer. The labels and source
        # numbers come exclusively from the rendered evidence assessment.
        repaired, appended = append_missing_enumeration_items(
            answer, final.enumeration
        )
        if appended and final.grounding_passed:
            answer = repaired
            compacted = compacted or appended
            final = assess_answer_completion(question, evidence_context, answer)
    valid = not final.correction_required and (
        validate_answer(answer)
        if validate_answer is not None
        else validate_grounded_answer(answer, evidence_context)
    )
    return AnswerCompletion(
        answer if valid else FALLBACK_ANSWER,
        initial,
        final,
        True,
        valid,
        "+".join(reasons),
        compacted,
    )


def completion_metadata(outcome: AnswerCompletion) -> dict[str, Any]:
    """Serialize stable fields shared by runner, checkpoint, and admission."""
    period = outcome.initial.period_value.period_value
    initial_period_passed = not period.applicable or period.passed
    final_period = outcome.final.period_value.period_value
    final_period_passed = not final_period.applicable or final_period.passed
    initial_enumeration_passed = (
        not outcome.initial.enumeration.applicable
        or outcome.initial.enumeration.passed
    )
    final_enumeration_passed = (
        not outcome.final.enumeration.applicable
        or outcome.final.enumeration.passed
    )
    return {
        "applicable": period.applicable or outcome.initial.enumeration.applicable,
        "period_value_applicable": period.applicable,
        "enumeration_applicable": outcome.initial.enumeration.applicable,
        "enumeration_kind": outcome.initial.enumeration.kind,
        "evidence_items": [
            {
                "label": item.label,
                "aliases": list(item.aliases),
                "source_number": item.source_number,
                "evidence_kind": item.evidence_kind,
            }
            for item in outcome.initial.enumeration.evidence_items
        ],
        "covered_items": [
            item.label for item in outcome.initial.enumeration.covered_items
        ],
        "missing_items": [
            item.label for item in outcome.initial.enumeration.missing_items
        ],
        "initial_overdetailed": outcome.initial.enumeration.overdetailed,
        "final_covered_items": [
            item.label for item in outcome.final.enumeration.covered_items
        ],
        "final_missing_items": [
            item.label for item in outcome.final.enumeration.missing_items
        ],
        "final_overdetailed": outcome.final.enumeration.overdetailed,
        "initial_passed": initial_period_passed and initial_enumeration_passed,
        "final_passed": final_period_passed and final_enumeration_passed,
        "correction_attempted": outcome.correction_attempted,
        "correction_attempts": int(outcome.correction_attempted),
        "correction_accepted": outcome.correction_accepted,
        "answer_compacted": outcome.answer_compacted,
        "initial_grounding_passed": outcome.initial.grounding_passed,
        "final_grounding_passed": outcome.final.grounding_passed,
        "initial_unsupported_numeric_claims": list(
            outcome.initial.unsupported_numeric_claims
        ),
        "final_unsupported_numeric_claims": list(
            outcome.final.unsupported_numeric_claims
        ),
        "correction_reason": outcome.correction_reason,
        "initial_missing_pairs": [
            {
                "label": pair.label,
                "period": pair.period,
                "value": pair.value,
                "source_number": pair.source_number,
            }
            for pair in outcome.initial.period_value.period_value.missing_pairs
        ],
    }
