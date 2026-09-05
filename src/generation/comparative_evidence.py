"""Provider-free fact extraction for multi-company comparisons.

The extractor is intentionally conservative. It records nearby evidence for
metric/value pairs, but it does not decide which company wins a comparison.
That decision belongs to a contract or renderer with an explicit compatibility
rule.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.company_entities import detect_tickers
from src.generation.period_value_completeness import EvidenceSource, parse_evidence_sources


COMPARATIVE_EVIDENCE_CONTRACT_VERSION = 2
COMPARATIVE_EVIDENCE_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-evidence-v2-metric-value-period-unit-source-compatibility"
).hexdigest()

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:[$€£]\s*)?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"(?:\s*(?:%|million|billion|thousand|bn|mm))?",
    re.IGNORECASE,
)
_METRIC_RE = re.compile(
    r"\b(?:microsoft\s+cloud\s+revenue|microsoft\s+cloud|cloud\s+revenue|"
    r"cloud\s+services|cloud|services\s+net\s+sales|services|net\s+sales|"
    r"total\s+revenue|revenue|sales|subscriptions?|depend(?:s|ence|ency)?)\b",
    re.IGNORECASE,
)
_SHARE_RE = re.compile(
    r"\b(?:share|proportion|percent(?:age)?\s+of|%\s+of|of\s+total)\b",
    re.IGNORECASE,
)
_DEPENDENCY_RE = re.compile(
    r"\b(?:depend(?:s|ed|ence|ency)|reli(?:es|ance|ant)|reliant)\b",
    re.IGNORECASE,
)
_VALUE_RE = re.compile(
    r"\b(?:higher|lower|more|less|largest|smallest|growth|grew|increase|"
    r"increased|decrease|decreased|value|amount|revenue|sales|depends?|"
    r"reliance|reliant)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ComparativeFact:
    """One metric/value candidate tied to one rendered source."""

    ticker: str
    source_number: int
    metric: str
    value: str
    period: str | None
    unit: str | None
    evidence_text: str
    has_explicit_share: bool

    @property
    def normalized_metric(self) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", self.metric.casefold()))


@dataclass(frozen=True)
class ComparativeQuestionIntent:
    """The comparison dimension requested by a question."""

    mode: str
    metric_terms: tuple[str, ...]
    requested_periods: tuple[str, ...]
    requires_numeric_evidence: bool
    requires_share_evidence: bool


def _compact(value: str) -> str:
    return " ".join(value.split())


def _source_ticker(source: EvidenceSource) -> str | None:
    tickers = detect_tickers(source.citation)
    return tickers[0] if len(tickers) == 1 else None


def _unit_for_value(value: str, window: str, source_text: str) -> str | None:
    lowered = value.casefold()
    if "%" in value or re.search(r"\bpercent(?:age)?\b", lowered):
        return "%"
    for unit in ("billion", "million", "thousand", "bn", "mm"):
        if re.search(rf"\b{re.escape(unit)}\b", lowered):
            return unit
    if (
        "$" in value
        or "dollars" in window.casefold()
        or "usd" in window.casefold()
        or re.search(r"\bdollars?\s+in\s+millions?\b", source_text, re.I)
    ):
        # A table-level unit applies to the row when the source explicitly
        # declares its scale. It is still attached to this source, never to a
        # fact from another company.
        if re.search(r"\b(?:in|dollars? in)\s+millions?\b", source_text, re.I):
            return "million USD"
        return "USD"
    return None


def _metric_for_window(window: str) -> str | None:
    matches = list(_METRIC_RE.finditer(window))
    if not matches:
        return None
    # Prefer the most specific phrase present near the value.
    return max(matches, key=lambda match: len(match.group(0))).group(0)


def _metric_for_position(text: str, start: int, end: int) -> str | None:
    """Find a metric label immediately before a value in prose or a table."""
    preceding_start = max(0, start - 90)
    preceding = text[preceding_start:start]
    matches = list(_METRIC_RE.finditer(preceding))
    if matches:
        match = matches[-1]
        between = text[preceding_start + match.end() : start]
        # A metric from the preceding sentence cannot authorize a number in a
        # filing footer, page marker, or unrelated following sentence.
        if "." in between or ";" in between:
            return None
        return match.group(0)
    return None


def _evidence_window(text: str, start: int, end: int) -> str:
    left = max(0, start - 100)
    right = min(len(text), end + 100)
    return _compact(text[left:right]).strip(" -:;,.\n")


def _segment_for_position(text: str, start: int, end: int) -> str:
    """Return one sentence/table row around a numeric token."""
    punctuation_positions = [
        position
        for position in range(max(0, start - 180), start)
        if text[position] in ".;"
        and not (
            text[position] == "."
            and position > 0
            and position + 1 < len(text)
            and text[position - 1].isdigit()
            and text[position + 1].isdigit()
        )
    ]
    left_boundaries = [text.rfind("\n", 0, start), *(punctuation_positions or [-1])]
    left = max(left_boundaries) + 1
    right_candidates = []
    for position in (text.find("\n", end), text.find(".", end), text.find(";", end)):
        if position < 0:
            continue
        if (
            text[position] == "."
            and position > 0
            and position + 1 < len(text)
            and text[position - 1].isdigit()
            and text[position + 1].isdigit()
        ):
            continue
        right_candidates.append(position)
    right = min(right_candidates) if right_candidates else len(text)
    segment = _compact(text[left:right]).strip(" -:,.\n")
    if len(segment) < 12:
        return _evidence_window(text, start, end)
    return segment


def extract_comparative_facts(
    question: str,
    evidence_context: str,
) -> dict[str, tuple[ComparativeFact, ...]]:
    """Extract metric/value candidates grouped by company ticker."""
    expected = detect_tickers(question)
    result: dict[str, list[ComparativeFact]] = {ticker: [] for ticker in expected}
    for source in parse_evidence_sources(evidence_context):
        ticker = _source_ticker(source)
        if ticker not in result:
            continue
        text = source.text
        for match in _NUMBER_RE.finditer(text):
            value = _compact(match.group(0))
            if _YEAR_RE.fullmatch(value.replace(",", "")):
                continue
            window = _segment_for_position(text, match.start(), match.end())
            metric = _metric_for_position(text, match.start(), match.end())
            if metric is None:
                continue
            periods = tuple(dict.fromkeys(_YEAR_RE.findall(window)))
            result[ticker].append(
                ComparativeFact(
                    ticker=ticker,
                    source_number=source.number,
                    metric=metric,
                    value=value,
                    period=periods[-1] if periods else None,
                    unit=_unit_for_value(value, window, text),
                    evidence_text=window,
                    has_explicit_share=bool(_SHARE_RE.search(window)),
                )
            )
    return {ticker: tuple(facts) for ticker, facts in result.items()}


def classify_comparative_question(question: str) -> ComparativeQuestionIntent:
    """Classify only the comparison dimension expressed in the question."""
    lowered = question.casefold()
    periods = tuple(dict.fromkeys(_YEAR_RE.findall(question)))
    if _DEPENDENCY_RE.search(question):
        mode = "dependency"
    elif re.search(r"\b(?:growth|grew|increase|decrease|trend)\b", lowered):
        mode = "growth"
    elif re.search(r"\b(?:higher|lower|largest|smallest|value|amount)\b", lowered):
        mode = "value"
    else:
        mode = "qualitative"
    terms: list[str] = []
    if re.search(r"\bcloud\b|\bazure\b|\baws\b", lowered):
        terms.append("cloud")
    if re.search(r"\bsubscription", lowered):
        terms.append("subscription")
    if re.search(r"\bservices?\b", lowered):
        terms.append("services")
    if re.search(r"\brevenue|sales\b", lowered):
        terms.append("revenue")
    return ComparativeQuestionIntent(
        mode=mode,
        metric_terms=tuple(dict.fromkeys(terms)),
        requested_periods=periods,
        requires_numeric_evidence=mode in {"dependency", "growth", "value"}
        or bool(_VALUE_RE.search(question)),
        requires_share_evidence=mode == "dependency",
    )


def facts_match_intent(
    question: str,
    facts_by_ticker: dict[str, tuple[ComparativeFact, ...]],
) -> dict[str, tuple[ComparativeFact, ...]]:
    """Keep facts with the requested metric and period when possible."""
    intent = classify_comparative_question(question)
    terms = intent.metric_terms
    if intent.mode == "dependency":
        specific_terms = tuple(term for term in terms if term != "revenue")
        if specific_terms:
            terms = specific_terms
    aliases = {
        "cloud": ("cloud", "azure", "aws"),
        "subscription": ("subscription", "services"),
        "services": ("services", "subscription"),
        "revenue": ("revenue", "sales", "net sales"),
    }
    selected: dict[str, tuple[ComparativeFact, ...]] = {}
    for ticker, facts in facts_by_ticker.items():
        matching = tuple(
            fact
            for fact in facts
            if (
                not terms
                or any(
                    alias in fact.normalized_metric
                    for term in terms
                    for alias in aliases.get(term, (term,))
                )
            )
            and (
                not intent.requested_periods
                or fact.period is None
                or fact.period in intent.requested_periods
            )
        )
        # For a dependency question, a generic revenue/sales fact is not a
        # valid substitute for a requested cloud/services branch. Falling back
        # to arbitrary facts would recreate the original false-positive guard.
        selected[ticker] = (
            matching
            if intent.mode == "dependency" and any(term != "revenue" for term in terms)
            else matching or facts
        )
    return selected
