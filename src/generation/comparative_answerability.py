"""Conservative, provider-free answerability checks for comparisons."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.company_entities import detect_tickers
from src.generation.period_value_completeness import (
    EvidenceSource,
    parse_evidence_sources,
)


COMPARATIVE_ANSWERABILITY_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-answerability-v1-balanced-entity-branch-intent-and-value-evidence"
).hexdigest()

_FALLBACK_PHRASE = "could not find sufficient information"
_NUMERIC_COMPARISON_RE = re.compile(
    r"\b(depends|higher|lower|more|less|revenue|sales|growth|value|amount)\b",
    re.IGNORECASE,
)
_NUMERIC_EVIDENCE_RE = re.compile(
    r"(?<![A-Za-z])(?:[$€£]\s*)?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"(?:\s*(?:%|million|billion|thousand|bn|mm))?\b",
    re.IGNORECASE,
)
_INTENT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "cloud": ("cloud", "azure", "aws"),
    "cybersecurity": (
        "cybersecurity",
        "cyber",
        "security",
        "data loss",
        "unauthorized access",
    ),
    "growth": ("growth", "increase", "increased", "grew", "year-over-year"),
    "international": ("international", "foreign", "global", "geopolitical"),
    "operations": ("operations", "operational"),
    "revenue": ("revenue", "sales", "net sales"),
    "risk": ("risk", "risks", "threat"),
    "services": ("services", "service", "subscription", "subscriptions"),
}
_STOPWORDS = {
    "amazon",
    "apple",
    "approach",
    "business",
    "company",
    "compare",
    "depends",
    "discloses",
    "disclosures",
    "factor",
    "factors",
    "fiscal",
    "from",
    "higher",
    "less",
    "microsoft",
    "more",
    "most",
    "their",
    "terms",
    "what",
    "which",
    "with",
    "year",
}


@dataclass(frozen=True)
class ComparativeAnswerabilityAssessment:
    """Audit one comparative draft against its rendered source branches."""

    applicable: bool
    expected_tickers: tuple[str, ...]
    evidenced_tickers: tuple[str, ...]
    missing_tickers: tuple[str, ...]
    intent_groups: tuple[str, ...]
    branch_intent_coverage: dict[str, tuple[str, ...]]
    numeric_evidence_by_ticker: dict[str, bool]
    evidence_sufficient: bool
    draft_is_fallback: bool
    retry_required: bool

    @property
    def passed(self) -> bool:
        """A safe fallback passes when evidence is genuinely insufficient."""
        return (
            not self.applicable
            or not self.draft_is_fallback
            or not self.evidence_sufficient
        )

    @property
    def requires_buffering(self) -> bool:
        """Return whether a stream must finish before emitting the draft."""
        return self.applicable and self.evidence_sufficient


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _intent_groups(question: str) -> tuple[str, ...]:
    tokens = re.findall(r"[a-z0-9]+", question.casefold())
    groups: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < 4 or token in _STOPWORDS:
            continue
        group = next(
            (
                candidate
                for candidate, alternatives in _INTENT_SYNONYMS.items()
                if token == candidate or token in alternatives
            ),
            None,
        )
        if group is None:
            continue
        if group not in seen:
            seen.add(group)
            groups.append(group)
    return tuple(groups)


def _intent_hits(text: str, groups: tuple[str, ...]) -> tuple[str, ...]:
    normalized = _normalize(text)
    return tuple(
        group
        for group in groups
        if any(_normalize(term) in normalized for term in _INTENT_SYNONYMS.get(group, (group,)))
    )


def _source_ticker(source: EvidenceSource) -> str | None:
    tickers = detect_tickers(source.citation)
    return tickers[0] if len(tickers) == 1 else None


def assess_comparative_answerability(
    question: str,
    evidence_context: str,
    answer: str,
) -> ComparativeAnswerabilityAssessment:
    """Determine whether a fallback is unsafe to keep.

    The audit is deliberately conservative. It requires at least two known
    entities, one rendered source for every entity, intent coverage for every
    branch, and numeric evidence for questions that ask for a quantitative
    comparison. It never reads evaluation labels or expected answers.
    """
    expected = detect_tickers(question)
    applicable = len(expected) >= 2
    sources = parse_evidence_sources(evidence_context)
    by_ticker: dict[str, list[EvidenceSource]] = {ticker: [] for ticker in expected}
    for source in sources:
        ticker = _source_ticker(source)
        if ticker in by_ticker:
            by_ticker[ticker].append(source)

    evidenced = tuple(ticker for ticker in expected if by_ticker[ticker])
    missing = tuple(ticker for ticker in expected if not by_ticker[ticker])
    groups = _intent_groups(question)
    coverage = {
        ticker: _intent_hits(
            "\n".join(source.text for source in by_ticker[ticker]), groups
        )
        for ticker in expected
    }
    numeric_required = bool(_NUMERIC_COMPARISON_RE.search(question))
    numeric_evidence = {
        ticker: bool(
            _NUMERIC_EVIDENCE_RE.search(
                "\n".join(source.text for source in by_ticker[ticker])
            )
        )
        for ticker in expected
    }
    intent_sufficient = bool(groups) and all(
        coverage[ticker] for ticker in expected
    )
    evidence_sufficient = bool(
        applicable
        and not missing
        and intent_sufficient
        and (not numeric_required or all(numeric_evidence.values()))
    )
    draft_is_fallback = _FALLBACK_PHRASE in answer.casefold()
    return ComparativeAnswerabilityAssessment(
        applicable=applicable,
        expected_tickers=expected,
        evidenced_tickers=evidenced,
        missing_tickers=missing,
        intent_groups=groups,
        branch_intent_coverage=coverage,
        numeric_evidence_by_ticker=numeric_evidence,
        evidence_sufficient=evidence_sufficient,
        draft_is_fallback=draft_is_fallback,
        retry_required=draft_is_fallback and evidence_sufficient,
    )
