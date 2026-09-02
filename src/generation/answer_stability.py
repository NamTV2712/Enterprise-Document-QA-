"""Conservative, evidence-only answer stability checks.

The existing completion policy already handles table-shaped period/value rows
and exhaustive enumerations.  This module covers the remaining narrow gap:
growth or trend questions whose evidence states the required numeric facts in
prose instead of a year/value table.  It derives anchors from the rendered
evidence and the question only; it never reads benchmark answers or labels.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.generation.period_value_completeness import parse_evidence_sources


ANSWER_STABILITY_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"answer-stability-v1-query-anchored-prose-numeric-facts-earliest-source-no-derived-values"
).hexdigest()

_NUMERIC_INTENT_RE = re.compile(
    r"\b(growth|grew|grown|trend|trended|increase|increased|decrease|"
    r"decreased|change|changed|year[- ]over[- ]year|higher|lower)\b",
    re.IGNORECASE,
)
_GROWTH_EVIDENCE_RE = re.compile(
    r"\b(growth|grew|grown|increas(?:e|ed|ing)|decreas(?:e|ed|ing)|"
    r"declin(?:e|ed|ing)|year[- ]over[- ]year|higher|lower|driven by)\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(
    r"(?<![\w])(?:[$€£]\s*)?\(?\d[\d,]*(?:\.\d+)?\)?"
    r"(?:\s*(?:%|million|billion|trillion|thousand|basis points?))?"
    r"(?![\w])",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
_TOPIC_ANCHOR_RE = re.compile(
    r"\b(?:aws|azure|linkedin|dynamics|gaming|xbox|windows|surface|"
    r"copilot|microsoft\s+cloud|microsoft\s+365)\b",
    re.IGNORECASE,
)

_QUESTION_STOPWORDS = {
    "about", "amazon", "and", "apple", "are", "business", "change",
    "cloud", "company", "compare", "compared", "companies", "describe",
    "describes", "does", "from", "fiscal", "for", "growth", "how", "in",
    "its", "microsoft", "of", "on", "over", "revenue", "services", "terms",
    "the", "their", "to", "trend", "was", "what", "which", "with", "year",
    "years",
}


@dataclass(frozen=True)
class NumericEvidenceFact:
    """One exact numeric token anchored to a relevant evidence sentence."""

    value: str
    source_number: int
    sentence: str

    @property
    def key(self) -> str:
        return _numeric_key(self.value)


@dataclass(frozen=True)
class AnswerStabilityAssessment:
    """Provider-free completeness result for prose numeric summaries."""

    applicable: bool
    kind: str | None
    expected_facts: tuple[NumericEvidenceFact, ...]
    covered_facts: tuple[NumericEvidenceFact, ...]
    missing_facts: tuple[NumericEvidenceFact, ...]
    passed: bool

    @property
    def correction_required(self) -> bool:
        return self.applicable and not self.passed


def _question_terms(question: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", question.casefold())
        if len(token) >= 3 and token not in _QUESTION_STOPWORDS
    }


def _sentences(text: str) -> tuple[str, ...]:
    return tuple(
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if sentence.strip()
    )


def _numeric_key(value: str) -> str:
    """Normalize presentation noise while preserving unit and magnitude."""
    normalized = value.casefold().strip(" .,:;—–-_")
    normalized = re.sub(r"[$€£]", "", normalized)
    normalized = normalized.replace(",", "")
    return re.sub(r"\s+", "", normalized)


def _is_relevant_number(value: str) -> bool:
    bare = value.strip().replace("$", "").replace("€", "").replace("£", "")
    bare = bare.strip("() .,;:")
    if _YEAR_RE.fullmatch(bare):
        return False
    # Unitless single numbers in prose are often table row indices or counts.
    # Require a currency sign, a decimal/comma, or an explicit unit/percent.
    return bool(
        re.search(r"[$€£%.,]|\b(?:million|billion|trillion|thousand|basis)\b", value, re.I)
    )


def _extract_facts(
    question: str,
    evidence_context: str,
) -> tuple[NumericEvidenceFact, ...]:
    question_terms = _question_terms(question)
    if not question_terms:
        return ()
    normalized_question = question.casefold()
    question_anchors = {
        match.group(0).casefold()
        for match in _TOPIC_ANCHOR_RE.finditer(question)
    }
    asks_about_microsoft_cloud = (
        "microsoft" in normalized_question and "cloud" in normalized_question
    )

    # Match the earliest source that has enough query-anchored growth facts.
    # Later chunks can repeat a label for a different metric; merging them
    # would create a false completeness obligation.
    for source in parse_evidence_sources(evidence_context):
        facts: list[NumericEvidenceFact] = []
        seen: set[str] = set()
        for sentence in _sentences(source.text):
            if not _GROWTH_EVIDENCE_RE.search(sentence):
                continue
            sentence_terms = set(re.findall(r"[a-z0-9]+", sentence.casefold()))
            sentence_anchors = {
                match.group(0).casefold()
                for match in _TOPIC_ANCHOR_RE.finditer(sentence)
            }
            is_microsoft_cloud_anchor = (
                asks_about_microsoft_cloud
                and re.search(r"\bmicrosoft\s+cloud\b", sentence, re.I) is not None
            )
            if question_anchors:
                query_anchor_match = bool(question_anchors & sentence_anchors)
            else:
                query_anchor_match = bool(question_terms & sentence_terms)
            if not query_anchor_match and not is_microsoft_cloud_anchor:
                continue
            for match in _NUMBER_RE.finditer(sentence):
                value = re.sub(r"\s+", " ", match.group(0)).strip()
                if not _is_relevant_number(value):
                    continue
                key = _numeric_key(value)
                if key in seen:
                    continue
                seen.add(key)
                facts.append(NumericEvidenceFact(value, source.number, sentence))
        if len(facts) >= 2:
            return tuple(facts)
    return ()


def _answer_numeric_keys(answer: str) -> set[str]:
    return {
        _numeric_key(match.group(0))
        for match in _NUMBER_RE.finditer(answer)
        if _is_relevant_number(match.group(0))
    }


def assess_answer_stability(
    question: str,
    evidence_context: str,
    answer: str,
) -> AnswerStabilityAssessment:
    """Check exact prose numeric anchors for growth/trend-style questions."""
    if not _NUMERIC_INTENT_RE.search(question):
        return AnswerStabilityAssessment(False, None, (), (), (), True)

    expected = _extract_facts(question, evidence_context)
    if not expected:
        return AnswerStabilityAssessment(False, None, (), (), (), True)

    answer_keys = _answer_numeric_keys(answer)
    covered = tuple(fact for fact in expected if fact.key in answer_keys)
    missing = tuple(fact for fact in expected if fact.key not in answer_keys)
    return AnswerStabilityAssessment(
        True,
        "query_anchored_numeric_summary",
        expected,
        covered,
        missing,
        not missing,
    )
