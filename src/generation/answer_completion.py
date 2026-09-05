"""One bounded, evidence-only completion pass for generated answers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from src.generation.enumeration_completeness import (
    ENUMERATION_COMPLETENESS_FINGERPRINT,
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
from src.generation.answer_stability import (
    ANSWER_STABILITY_FINGERPRINT,
    AnswerStabilityAssessment,
    assess_answer_stability,
)
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
    ComparativeAnswerabilityAssessment,
    assess_comparative_answerability,
)
from src.generation.comparative_answer_renderer import (
    COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
    render_deterministic_comparative_answer,
)
from src.generation.prompt_contracts import (
    COMPARATIVE_NUMERIC_UNIT_CONTRACT,
    COMPARATIVE_NUMERIC_UNIT_CONTRACT_FINGERPRINT,
    RISK_COMPARISON_CONTRACT_FINGERPRINT,
    RISK_FOCUS_CONTRACT_FINGERPRINT,
)
from src.generation.risk_answer_shape import (
    RISK_ANSWER_SHAPE_FINGERPRINT,
    render_deterministic_risk_answer,
)
from src.generation.evidence_fact_renderer import (
    EVIDENCE_FACT_RENDERER_FINGERPRINT,
    render_deterministic_fact,
)
from src.generation.enumeration_answer_renderer import (
    ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
    render_deterministic_revenue_answer,
)


ANSWER_COMPLETION_FINGERPRINT = "sha256:" + hashlib.sha256(
    (
        b"answer-completion-v12-generic-enumeration-boundary-revenue-granularity-"
        b"scoped-bullet-compaction-grouped-home-alias-evidence-label-repair-"
        b"revenue-top-level-dedup-generic-numeric-grounding-repair-period-value-"
        b"one-correction-answer-stability-"
        b"risk-evidence-roles-primary-supporting-"
        b"enumeration-fingerprint-"
        + ENUMERATION_COMPLETENESS_FINGERPRINT.encode()
        + b"-risk-focus-fingerprint-"
        + RISK_FOCUS_CONTRACT_FINGERPRINT.encode()
        + b"-"
        + ANSWER_STABILITY_FINGERPRINT.encode()
        + b"-comparative-answerability-fingerprint-"
        + COMPARATIVE_ANSWERABILITY_FINGERPRINT.encode()
        + b"-comparative-answer-renderer-fingerprint-"
        + COMPARATIVE_ANSWER_RENDERER_FINGERPRINT.encode()
        + b"-comparative-numeric-unit-contract-fingerprint-"
        + COMPARATIVE_NUMERIC_UNIT_CONTRACT_FINGERPRINT.encode()
        + b"-risk-answer-shape-fingerprint-"
        + RISK_ANSWER_SHAPE_FINGERPRINT.encode()
        + b"-evidence-fact-renderer-fingerprint-"
        + EVIDENCE_FACT_RENDERER_FINGERPRINT.encode()
        + b"-enumeration-answer-renderer-fingerprint-"
        + ENUMERATION_ANSWER_RENDERER_FINGERPRINT.encode()
        + b"-risk-comparison-contract-fingerprint-"
        + RISK_COMPARISON_CONTRACT_FINGERPRINT.encode()
        + b"-revenue-main-vs-exhaustive-scope"
    )
).hexdigest()


class AnswerCompletionError(PeriodValueCorrectionError):
    """Provider failure while attempting the single bounded correction."""


@dataclass(frozen=True)
class AnswerCompletionAssessment:
    """Combined deterministic assessment before or after correction."""

    period_value: GroundedCompletionAssessment
    enumeration: EnumerationCompleteness
    stability: AnswerStabilityAssessment
    answerability: ComparativeAnswerabilityAssessment
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
    answer_rendered_deterministically: bool = False


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
    stability = assess_answer_stability(question, evidence_context, answer)
    answerability = assess_comparative_answerability(
        question, evidence_context, answer
    )
    # Table-shaped period/value evidence has its own stricter detector. Avoid
    # adding prose anchors from another source to the same correction request.
    if period_value.period_value.applicable:
        stability = AnswerStabilityAssessment(False, None, (), (), (), True)
    enumeration = assess_enumeration_completeness(
        question, evidence_context, answer
    )
    if enumeration.applicable:
        grounding_passed, unsupported_numeric_claims = _answer_contract_audit(
            answer, evidence_context
        )
        correction_required = (
            not enumeration.passed
            or not grounding_passed
            or stability.correction_required
            or answerability.retry_required
        )
    elif period_value.period_value.applicable:
        grounding_passed = period_value.grounding_passed
        unsupported_numeric_claims = period_value.unsupported_numeric_claims
        correction_required = (
            period_value.correction_required
            or stability.correction_required
            or answerability.retry_required
        )
    else:
        # Keep the unified postprocessor lightweight for ordinary qualitative
        # answers, but do not let an unsupported numeric claim bypass the
        # shared grounding contract merely because the conservative
        # period/value detector did not classify the question as numeric.
        grounding_passed, unsupported_numeric_claims = _answer_contract_audit(
            answer, evidence_context
        )
        correction_required = (
            bool(unsupported_numeric_claims)
            or stability.correction_required
            or answerability.retry_required
        )
    return AnswerCompletionAssessment(
        period_value,
        enumeration,
        stability,
        answerability,
        grounding_passed,
        unsupported_numeric_claims,
        correction_required,
    )


def answer_completion_requires_buffering(
    question: str,
    evidence_context: str,
) -> bool:
    """Return whether a generated stream must be buffered for completion."""
    assessment = assess_answer_completion(question, evidence_context, "")
    return (
        assessment.correction_required
        or assessment.answerability.requires_buffering
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
            f"- Source {item.source_number} ({item.evidence_role}): {item.label}"
            for item in assessment.enumeration.missing_items
        )
        sections.append(
            "The draft omitted these explicit evidence-backed enumeration "
            f"items:\n{missing}"
        )
    if assessment.enumeration.applicable and assessment.enumeration.overdetailed:
        sections.append(
            "The draft is over-detailed for the requested enumeration. Keep "
            "one concise bullet per canonical filing category with a brief "
            "source-backed descriptor. Preserve every "
            "supporting/cross-cutting evidence item in one compact grouped "
            "section, but do not make consequences, examples, sub-products, "
            "features, or sub-risks into separate peer bullets."
        )
    if (
        assessment.enumeration.applicable
        and assessment.enumeration.ambiguous_items
    ):
        sections.append(
            "Enumeration evidence was insufficient or ambiguous; do not add "
            "unsupported categories."
        )
    if assessment.stability.applicable and assessment.stability.missing_facts:
        missing = "\n".join(
            f"- Source {fact.source_number}: {fact.value}"
            for fact in assessment.stability.missing_facts
        )
        sections.append(
            "The draft omitted these exact query-anchored numeric facts from "
            f"the evidence:\n{missing}"
        )
    if assessment.unsupported_numeric_claims:
        sections.append(
            "Remove numeric claims not printed in the cited evidence: "
            + ", ".join(assessment.unsupported_numeric_claims)
        )
    if assessment.answerability.retry_required:
        branches = ", ".join(assessment.answerability.expected_tickers)
        sections.append(
            "The draft returned the fallback even though the rendered evidence "
            f"contains balanced, intent-matched branches for {branches}. Answer "
            "the comparison from those branches only, cite each factual claim, "
            "and preserve every value exactly as printed."
        )
    if (
        assessment.answerability.comparison_mode == "dependency"
        and assessment.answerability.qualified
    ):
        sections.append(
            "Do not infer dependency from absolute revenue amounts. Report the "
            "company-specific measures and state that different measures or "
            "missing disclosed shares do not support a dependency ranking."
        )
    if assessment.answerability.applicable:
        sections.append(COMPARATIVE_NUMERIC_UNIT_CONTRACT)
    details = "\n\n".join(sections)
    return (
        "Correct the draft using only the same SEC evidence below. Return one "
        "concise final answer only. Preserve canonical [Source N] citations, "
        "include every required enumeration item exactly once, "
        "present canonical categories first with brief source-backed descriptors "
        "and include supporting/cross-cutting items as a compact grouped "
        "section only for exhaustive enumeration questions. Do not add items from "
        "general knowledge. Quote values exactly as "
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
    deterministic_risk_renderer: bool = False,
    deterministic_fact_renderer: bool = False,
    deterministic_revenue_renderer: bool = False,
    deterministic_comparative_renderer: bool = False,
) -> AnswerCompletion:
    """Apply at most one provider correction for the scoped contracts."""
    initial = assess_answer_completion(question, evidence_context, draft_answer)
    if deterministic_comparative_renderer:
        rendered = render_deterministic_comparative_answer(
            question, evidence_context
        )
        if rendered:
            final = assess_answer_completion(question, evidence_context, rendered)
            valid = (
                validate_answer(rendered)
                if validate_answer is not None
                else validate_grounded_answer(rendered, evidence_context)
            )
            if valid and not final.correction_required:
                return AnswerCompletion(
                    answer=rendered,
                    initial=initial,
                    final=final,
                    correction_attempted=False,
                    correction_accepted=True,
                    correction_reason="deterministic_comparative_renderer",
                    answer_compacted=True,
                    answer_rendered_deterministically=True,
                )
    if deterministic_fact_renderer:
        rendered = render_deterministic_fact(question, evidence_context)
        if rendered:
            final = assess_answer_completion(question, evidence_context, rendered)
            valid = (
                validate_answer(rendered)
                if validate_answer is not None
                else validate_grounded_answer(rendered, evidence_context)
            )
            if valid and not final.correction_required:
                return AnswerCompletion(
                    answer=rendered,
                    initial=initial,
                    final=final,
                    correction_attempted=False,
                    correction_accepted=True,
                    correction_reason="deterministic_fact_renderer",
                    answer_compacted=True,
                    answer_rendered_deterministically=True,
                )
    if deterministic_revenue_renderer:
        rendered = render_deterministic_revenue_answer(question, evidence_context)
        if rendered:
            final = assess_answer_completion(question, evidence_context, rendered)
            valid = (
                validate_answer(rendered)
                if validate_answer is not None
                else validate_grounded_answer(rendered, evidence_context)
            )
            if valid and not final.correction_required:
                return AnswerCompletion(
                    answer=rendered,
                    initial=initial,
                    final=final,
                    correction_attempted=False,
                    correction_accepted=True,
                    correction_reason="deterministic_revenue_renderer",
                    answer_compacted=True,
                    answer_rendered_deterministically=True,
                )
    if deterministic_risk_renderer and initial.enumeration.applicable:
        rendered = render_deterministic_risk_answer(
            question, evidence_context
        )
        if rendered:
            final = assess_answer_completion(question, evidence_context, rendered)
            valid = (
                validate_answer(rendered)
                if validate_answer is not None
                else validate_grounded_answer(rendered, evidence_context)
            )
            if valid and not final.correction_required:
                return AnswerCompletion(
                    answer=rendered,
                    initial=initial,
                    final=final,
                    correction_attempted=False,
                    correction_accepted=True,
                    correction_reason="deterministic_risk_renderer",
                    answer_compacted=True,
                    answer_rendered_deterministically=True,
                )
    if not initial.correction_required:
        answer, compacted = compact_enumeration_answer(
            draft_answer,
            initial.enumeration,
            evidence_context,
            apply_revenue_scope=deterministic_revenue_renderer,
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
    if initial.stability.correction_required:
        reasons.append("missing_query_anchored_numeric_facts")
    if initial.answerability.retry_required:
        reasons.append("answerable_fallback")
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
        corrected,
        corrected_assessment.enumeration,
        evidence_context,
        apply_revenue_scope=deterministic_revenue_renderer,
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
        "applicable": (
            period.applicable
            or outcome.initial.enumeration.applicable
            or outcome.initial.stability.applicable
            or outcome.initial.answerability.applicable
        ),
        "period_value_applicable": period.applicable,
        "enumeration_applicable": outcome.initial.enumeration.applicable,
        "stability_applicable": outcome.initial.stability.applicable,
        "answerability_applicable": outcome.initial.answerability.applicable,
        "answerability_evidence_sufficient": (
            outcome.initial.answerability.evidence_sufficient
        ),
        "answerability_retry_required": (
            outcome.initial.answerability.retry_required
        ),
        "answerability_status": outcome.initial.answerability.status,
        "answerability_comparison_mode": (
            outcome.initial.answerability.comparison_mode
        ),
        "answerability_reason_codes": list(
            outcome.initial.answerability.reason_codes
        ),
        "answerability_expected_tickers": list(
            outcome.initial.answerability.expected_tickers
        ),
        "answerability_evidenced_tickers": list(
            outcome.initial.answerability.evidenced_tickers
        ),
        "answerability_missing_tickers": list(
            outcome.initial.answerability.missing_tickers
        ),
        "answerability_branch_intent_coverage": {
            ticker: list(groups)
            for ticker, groups in outcome.initial.answerability.branch_intent_coverage.items()
        },
        "answerability_numeric_evidence_by_ticker": dict(
            outcome.initial.answerability.numeric_evidence_by_ticker
        ),
        "answerability_share_evidence_by_ticker": dict(
            outcome.initial.answerability.share_evidence_by_ticker
        ),
        "answerability_facts_by_ticker": {
            ticker: [
                {
                    "metric": fact.metric,
                    "value": fact.value,
                    "period": fact.period,
                    "unit": fact.unit,
                    "source_number": fact.source_number,
                    "has_explicit_share": fact.has_explicit_share,
                }
                for fact in facts
            ]
            for ticker, facts in outcome.initial.answerability.facts_by_ticker.items()
        },
        "answerability_qualified": outcome.initial.answerability.qualified,
        "deterministic_comparative_renderer": (
            outcome.answer_rendered_deterministically
            and outcome.correction_reason == "deterministic_comparative_renderer"
        ),
        "stability_kind": outcome.initial.stability.kind,
        "stability_expected_facts": [
            {
                "value": fact.value,
                "source_number": fact.source_number,
            }
            for fact in outcome.initial.stability.expected_facts
        ],
        "stability_covered_facts": [
            fact.value for fact in outcome.initial.stability.covered_facts
        ],
        "stability_missing_facts": [
            fact.value for fact in outcome.initial.stability.missing_facts
        ],
        "enumeration_kind": outcome.initial.enumeration.kind,
        "evidence_items": [
            {
                "label": item.label,
                "aliases": list(item.aliases),
                "source_number": item.source_number,
                "evidence_kind": item.evidence_kind,
                "evidence_role": item.evidence_role,
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
        "initial_passed": (
            initial_period_passed
            and initial_enumeration_passed
            and (
                not outcome.initial.stability.applicable
                or outcome.initial.stability.passed
            )
            and outcome.initial.answerability.passed
        ),
        "final_passed": (
            final_period_passed
            and final_enumeration_passed
            and (
                not outcome.final.stability.applicable
                or outcome.final.stability.passed
            )
            and outcome.final.answerability.passed
        ),
        "initial_stability_passed": (
            not outcome.initial.stability.applicable
            or outcome.initial.stability.passed
        ),
        "final_stability_passed": (
            not outcome.final.stability.applicable
            or outcome.final.stability.passed
        ),
        "final_stability_missing_facts": [
            fact.value for fact in outcome.final.stability.missing_facts
        ],
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
        "answer_rendered_deterministically": (
            outcome.answer_rendered_deterministically
        ),
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
