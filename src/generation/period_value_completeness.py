"""Evidence-derived completeness checks for multi-period monetary answers.

The detector is deliberately conservative. It activates only for a growth or
trend-style question and only when one rendered source contains a question-
matched table row beneath an explicit multi-year header. It never consumes
evaluation ground truth or required keywords.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable


PERIOD_VALUE_CORRECTION_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"period-value-completeness-v3-grounding-aware-one-correction"
).hexdigest()
FALLBACK_ANSWER = (
    "I could not find sufficient information in the available documents "
    "to answer this question with confidence."
)

_SOURCE_RE = re.compile(
    r"(?ms)^\[Source (?P<number>\d+)\] (?P<citation>[^\n]*)\n"
    r"(?P<text>.*?)(?=^\[Source \d+\] |\Z)"
)
_YEAR_RE = re.compile(r"^20\d{2}$")
_MONEY_VALUE_RE = re.compile(
    r"^\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?$"
)
_APPLICABLE_RE = re.compile(
    r"\b(growth|grew|grown|trend|trended|increase|increased|decrease|"
    r"decreased|year[- ]over[- ]year|higher|lower)\b",
    re.IGNORECASE,
)
_QUESTION_STOPWORDS = {
    "amazon", "apple", "business", "cloud", "company", "compare",
    "change", "did", "does", "fiscal", "from", "how", "microsoft",
    "over", "recent", "segment", "terms", "their", "total", "what",
    "which", "with", "year", "years",
}


@dataclass(frozen=True)
class PeriodValuePair:
    label: str
    period: str
    value: str
    source_number: int


@dataclass(frozen=True)
class EvidenceSource:
    number: int
    citation: str
    text: str


@dataclass(frozen=True)
class PeriodValueCompleteness:
    applicable: bool
    evidence_pairs: tuple[PeriodValuePair, ...]
    missing_pairs: tuple[PeriodValuePair, ...]
    passed: bool


@dataclass(frozen=True)
class GroundedCompletionAssessment:
    period_value: PeriodValueCompleteness
    grounding_passed: bool
    unsupported_numeric_claims: tuple[str, ...]
    correction_required: bool


@dataclass(frozen=True)
class PeriodValueCorrection:
    answer: str
    initial: PeriodValueCompleteness
    final: PeriodValueCompleteness
    correction_attempted: bool
    correction_accepted: bool
    initial_grounding_passed: bool = True
    final_grounding_passed: bool = True
    initial_unsupported_numeric_claims: tuple[str, ...] = ()
    final_unsupported_numeric_claims: tuple[str, ...] = ()
    correction_reason: str = ""


class PeriodValueCorrectionError(RuntimeError):
    """Provider failure while attempting the single bounded correction."""


def _question_terms(question: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", question.casefold())
        if len(token) >= 3 and token not in _QUESTION_STOPWORDS
    }


def _field(entry: Any, name: str, default: Any = "") -> Any:
    if isinstance(entry, dict):
        return entry.get(name, default)
    return getattr(entry, name, default)


def render_chunk_evidence(chunks: Iterable[Any]) -> str:
    """Render chunks with the canonical source numbering used by validators."""
    blocks: list[str] = []
    seen_ids: set[Any] = set()
    for chunk in chunks:
        chunk_id = _field(chunk, "chunk_id", None)
        if chunk_id is not None:
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
        citation = _field(chunk, "citation", "")
        text = _field(chunk, "text", "")
        # Trailing whitespace is not evidence. Normalizing it makes a parsed
        # Phase 2 block round-trip byte-identically through this adapter.
        blocks.append(
            f"[Source {len(blocks) + 1}] {citation}\n{str(text).rstrip()}"
        )
    return "\n\n".join(blocks)


def parse_evidence_sources(evidence_context: str) -> tuple[EvidenceSource, ...]:
    """Parse canonical source blocks without splitting internal blank lines."""
    return tuple(
        EvidenceSource(
            number=int(match.group("number")),
            citation=match.group("citation"),
            text=match.group("text").rstrip(),
        )
        for match in _SOURCE_RE.finditer(evidence_context)
        if match.group("text").strip()
    )


def validate_grounded_answer(answer: str, evidence_context: str) -> bool:
    """Require canonical citations and reject unsupported numeric claims."""
    # Keep the production validator aligned with the deterministic evaluator;
    # this import is local so the generation module remains lightweight.
    from src.evaluation.answer_contract import audit_answer

    sources = [source.text for source in parse_evidence_sources(evidence_context)]
    audit = audit_answer(answer, sources)
    return (
        bool(audit.canonical_citations)
        and not audit.fallback_answer
        and not audit.uncited_answer
        and not audit.out_of_range_citations
        and not audit.unsupported_numeric_claims
    )


def assess_grounded_completion(
    question: str,
    evidence_context: str,
    answer: str,
) -> GroundedCompletionAssessment:
    """Assess period/value completeness and grounding for applicable answers.

    A complete list of evidence values is not sufficient when the draft also
    adds a derived number that does not occur in the cited source.  Keep this
    check scoped to the conservative period/value detector so unrelated
    qualitative answers retain their existing generation path.
    """
    period_value = assess_period_value_completeness(
        question, evidence_context, answer
    )
    if not period_value.applicable:
        return GroundedCompletionAssessment(
            period_value, True, (), False
        )

    from src.evaluation.answer_contract import audit_answer

    source_texts = [source.text for source in parse_evidence_sources(evidence_context)]
    audit = audit_answer(answer, source_texts)
    grounding_passed = (
        bool(audit.canonical_citations)
        and not audit.fallback_answer
        and not audit.uncited_answer
        and not audit.out_of_range_citations
        and not audit.unsupported_numeric_claims
    )
    unsupported = tuple(audit.unsupported_numeric_claims)
    return GroundedCompletionAssessment(
        period_value,
        grounding_passed,
        unsupported,
        not period_value.passed or not grounding_passed,
    )


def _label_matches_question(label: str, question_terms: set[str]) -> bool:
    label_terms = set(re.findall(r"[a-z0-9]+", label.casefold()))
    return bool(label_terms & question_terms)


def _table_pairs(
    question: str,
    evidence_context: str,
) -> tuple[PeriodValuePair, ...]:
    question_terms = _question_terms(question)
    if not question_terms:
        return ()

    seen: set[tuple[int, str, str, str]] = set()
    for source_match in _SOURCE_RE.finditer(evidence_context):
        source_number = int(source_match.group("number"))
        source_pairs: list[PeriodValuePair] = []
        lines = [
            line.strip()
            for line in source_match.group("text").splitlines()
            if line.strip()
        ]
        index = 0
        while index < len(lines):
            if not _YEAR_RE.fullmatch(lines[index]):
                index += 1
                continue
            years: list[str] = []
            cursor = index
            while cursor < len(lines) and _YEAR_RE.fullmatch(lines[cursor]):
                years.append(lines[cursor])
                cursor += 1
            # Do not reinterpret the second/third year in one header as a new
            # shorter header; that silently shifts values onto wrong periods.
            index = cursor
            if len(years) < 2:
                continue

            # A table row should be nearby. Stop before the scan can drift into
            # an unrelated paragraph or another page-sized table.
            for row_index in range(cursor, min(len(lines), cursor + 40)):
                label = lines[row_index]
                if not _label_matches_question(label, question_terms):
                    continue
                values: list[str] = []
                value_cursor = row_index + 1
                while value_cursor < len(lines) and len(values) < len(years):
                    candidate = lines[value_cursor].replace("$", "").strip()
                    if _MONEY_VALUE_RE.fullmatch(candidate):
                        values.append(candidate)
                    elif re.search(r"[A-Za-z]", candidate):
                        break
                    value_cursor += 1
                if len(values) != len(years):
                    continue
                for period, value in zip(years, values, strict=True):
                    key = (source_number, label.casefold(), period, value)
                    if key in seen:
                        continue
                    seen.add(key)
                    source_pairs.append(
                        PeriodValuePair(label, period, value, source_number)
                    )
        # The earliest matching source is the highest-ranked evidence. Do not
        # merge same-label rows from later chunks where the surrounding metric
        # heading may describe a different measure (for example AWS operating
        # income rather than AWS net sales).
        if source_pairs:
            return tuple(source_pairs)
    return ()


def assess_period_value_completeness(
    question: str,
    evidence_context: str,
    answer: str,
) -> PeriodValueCompleteness:
    """Check whether all confidently extracted table pairs appear in answer."""
    if not _APPLICABLE_RE.search(question):
        return PeriodValueCompleteness(False, (), (), True)
    pairs = _table_pairs(question, evidence_context)
    if len(pairs) < 2:
        return PeriodValueCompleteness(False, pairs, (), True)
    folded_answer = answer.casefold()
    missing = tuple(
        pair
        for pair in pairs
        if pair.value.casefold() not in folded_answer
        or pair.period.casefold() not in folded_answer
    )
    return PeriodValueCompleteness(True, pairs, missing, not missing)


def build_period_value_correction_prompt(
    question: str,
    evidence_context: str,
    draft_answer: str,
    assessment: PeriodValueCompleteness,
    unsupported_numeric_claims: Iterable[str] = (),
) -> str:
    """Build one evidence-bound correction request from detected violations."""
    missing = "\n".join(
        f"- Source {pair.source_number}: {pair.label}, "
        f"{pair.period} = {pair.value}"
        for pair in assessment.missing_pairs
    )
    unsupported = tuple(dict.fromkeys(unsupported_numeric_claims))
    sections: list[str] = []
    if missing:
        sections.append(
            "The draft omitted these explicit evidence-derived period/value "
            f"pairs:\n{missing}"
        )
    if unsupported:
        claims = ", ".join(unsupported)
        sections.append(
            "The draft also contains numeric claims that are not present in "
            f"the cited evidence: {claims}. Remove them or replace them only "
            "with exact values stated in the evidence."
        )
    violations = "\n\n".join(sections)
    return (
        "Correct the draft answer using only the same SEC evidence below. "
        "Return one final answer only. Preserve canonical [Source N] citations "
        "and every grounded claim. Do not calculate, round, convert, or invent "
        f"any value. {violations}\n\nQuestion: {question}\n\n"
        f"Evidence:\n{evidence_context}\n\nDraft answer:\n{draft_answer}"
    )


def correct_period_value_once(
    question: str,
    evidence_context: str,
    draft_answer: str,
    generate_fn: Callable[[str], str],
    validate_answer: Callable[[str], bool] | None = None,
) -> PeriodValueCorrection:
    """Make at most one correction call, then pass or return safe fallback."""
    initial_assessment = assess_grounded_completion(
        question, evidence_context, draft_answer
    )
    initial = initial_assessment.period_value
    if not initial_assessment.correction_required:
        return PeriodValueCorrection(
            draft_answer,
            initial,
            initial,
            False,
            False,
            initial_assessment.grounding_passed,
            initial_assessment.grounding_passed,
            initial_assessment.unsupported_numeric_claims,
            initial_assessment.unsupported_numeric_claims,
            "",
        )

    reasons: list[str] = []
    if not initial.passed:
        reasons.append("missing_period_value_pairs")
    if not initial_assessment.grounding_passed:
        reasons.append("grounding_violation")
    try:
        corrected = generate_fn(
            build_period_value_correction_prompt(
                question,
                evidence_context,
                draft_answer,
                initial,
                initial_assessment.unsupported_numeric_claims,
            )
        )
    except Exception as error:
        raise PeriodValueCorrectionError(str(error)) from error
    final_assessment = assess_grounded_completion(
        question, evidence_context, corrected
    )
    final = final_assessment.period_value
    valid = final_assessment.correction_required is False and (
        validate_answer(corrected)
        if validate_answer is not None
        else validate_grounded_answer(corrected, evidence_context)
    )
    return PeriodValueCorrection(
        corrected if valid else FALLBACK_ANSWER,
        initial,
        final,
        True,
        valid,
        initial_assessment.grounding_passed,
        final_assessment.grounding_passed,
        initial_assessment.unsupported_numeric_claims,
        final_assessment.unsupported_numeric_claims,
        "+".join(reasons),
    )
