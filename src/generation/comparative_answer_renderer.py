"""Deterministic, qualified answers for evidence-limited comparisons."""

from __future__ import annotations

import hashlib
import re

from src.company_entities import detect_tickers
from src.generation.comparative_evidence import (
    ComparativeFact,
    classify_comparative_question,
    extract_comparative_facts,
    facts_match_intent,
)
from src.generation.period_value_completeness import parse_evidence_sources


COMPARATIVE_ANSWER_RENDERER_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-answer-renderer-v2-qualified-dependency-no-absolute-value-inference"
).hexdigest()

_DISPLAY_NAMES = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "MSFT": "Microsoft",
    "TSLA": "Tesla",
    "V": "Visa",
    "MA": "Mastercard",
}


def _display_name(ticker: str) -> str:
    return _DISPLAY_NAMES.get(ticker, ticker)


def _clean_evidence(fact: ComparativeFact) -> str:
    value = re.sub(r"\s+", " ", fact.value).strip()
    unit = fact.unit or ""
    if unit and unit != "%" and unit.casefold() not in value.casefold():
        value = f"{value} {unit}"
    metric = re.sub(r"\s+", " ", fact.metric).strip()
    return f"{metric} of {value}"


def _best_fact(facts: tuple[ComparativeFact, ...]) -> ComparativeFact | None:
    if not facts:
        return None

    def magnitude(fact: ComparativeFact) -> float:
        value = re.sub(r"[^0-9.]", "", fact.value)
        try:
            return float(value)
        except ValueError:
            return 0.0

    return max(
        facts,
        key=lambda fact: (
            fact.has_explicit_share,
            "gross margin" not in fact.evidence_text.casefold()
            or "net sales" in fact.evidence_text.casefold(),
            fact.unit is not None and fact.unit != "%",
            len(fact.normalized_metric),
            magnitude(fact),
        ),
    )


def render_dependency_comparison(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render a cautious dependency comparison only from explicit evidence."""
    intent = classify_comparative_question(question)
    tickers = detect_tickers(question)
    if intent.mode != "dependency" or len(tickers) < 2:
        return None
    facts = facts_match_intent(question, extract_comparative_facts(question, evidence_context))
    chosen = {ticker: _best_fact(facts.get(ticker, ())) for ticker in tickers}
    if any(fact is None for fact in chosen.values()):
        return None
    selected = [fact for fact in chosen.values() if fact is not None]
    # A dependency ranking is authoritative only when every branch exposes a
    # compatible share/proportion measure. Absolute revenue values and related
    # but non-identical measures must be reported as evidence, not ranked.
    explicit_share = all(fact.has_explicit_share for fact in selected)
    compatible_metrics = len({fact.normalized_metric for fact in selected}) == 1
    compatible_units = len({fact.unit for fact in selected}) == 1
    compatible_periods = len({fact.period for fact in selected}) == 1
    lines = [
        f"{_display_name(ticker)} disclosed {_clean_evidence(chosen[ticker])} "
        f"[Source {chosen[ticker].source_number}]."
        for ticker in tickers
    ]
    if explicit_share and compatible_metrics and compatible_units and compatible_periods:
        # The renderer deliberately preserves the facts but leaves any winner
        # determination to the provider when a full relation expression is
        # required. This branch is mostly for future explicit-share fixtures.
        lines.append(
            "The filings report the same-period, same-unit share measure for "
            "both companies, so these disclosed shares are directly comparable."
        )
    else:
        lines.append(
            "These are related but non-identical disclosures, so the reported "
            "amounts do not establish which company depends more on this revenue "
            "as a share of total revenue."
        )
    return " ".join(lines)


def render_deterministic_comparative_answer(
    question: str,
    evidence_context: str,
) -> str | None:
    """Try deterministic comparison renderers in a fixed order."""
    return render_dependency_comparison(question, evidence_context)
