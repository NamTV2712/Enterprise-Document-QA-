"""Deterministic, qualified answers for evidence-limited comparisons."""

from __future__ import annotations

import hashlib
import re

from src.company_entities import detect_tickers
from src.generation.comparative_evidence import (
    ComparativeFact,
    ComparativeFactV3,
    classify_comparative_question,
    extract_comparative_facts,
    select_dependency_evidence_v3,
    facts_match_intent,
)
from src.generation.period_value_completeness import parse_evidence_sources


COMPARATIVE_ANSWER_RENDERER_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-answer-renderer-v2-qualified-dependency-no-absolute-value-inference"
).hexdigest()
COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-answer-renderer-v3-bounded-disclosure-share-ranking-"
    b"evidence-contract-v3"
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


def _clean_v3_evidence(fact: ComparativeFactV3) -> str:
    """Display the source value without normalizing away its scope."""
    value = re.sub(r"\s+", " ", fact.value).strip()
    if fact.has_explicit_share and fact.denominator:
        return f"{value} of {fact.denominator}"
    unit = fact.unit or ""
    if unit and unit.casefold() not in value.casefold():
        value = f"{value} ({unit})"
    return value


def render_dependency_comparison_v3(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render the Evidence Contract v3 comparison from one shared selection.

    A ranking is emitted only for same-metric, same-denominator, same-period
    shares. Otherwise the renderer reports the bounded disclosures and makes
    no claim about information outside the supplied excerpts.
    """
    selection = select_dependency_evidence_v3(question, evidence_context)
    if not selection.evidence_sufficient:
        return None
    lines: list[str] = []
    for ticker in selection.expected_tickers:
        fact = selection.selected_by_ticker.get(ticker)
        excerpt = selection.excerpts_by_ticker.get(ticker)
        if fact is not None:
            lines.append(
                f"{_display_name(ticker)} disclosed {fact.metric} of "
                f"{_clean_v3_evidence(fact)} [Source {fact.source_number}]."
            )
        elif excerpt is not None:
            source_number, text = excerpt
            lines.append(
                f"{_display_name(ticker)}'s supplied excerpt states: {text} "
                f"[Source {source_number}]."
            )
    if selection.compatible:
        if len(selection.winners) == 1:
            winner = _display_name(selection.winners[0])
            lines.append(
                f"On this same-period, same-denominator share measure, "
                f"{winner} is higher; this conclusion is limited to the "
                "disclosed measure."
            )
        else:
            names = " and ".join(_display_name(ticker) for ticker in selection.winners)
            lines.append(
                f"The disclosed shares are equal for {names} on this "
                "same-period, same-denominator measure."
            )
    else:
        lines.append(
            "The supplied excerpts do not establish which company depends "
            "more on this revenue as a share of total revenue; this is a "
            "bounded conclusion about the excerpts, not the full filings."
        )
    return " ".join(lines)


def render_deterministic_comparative_answer_v3(
    question: str,
    evidence_context: str,
) -> str | None:
    """Opt-in v3 deterministic renderer; production remains on the v2 API."""
    return render_dependency_comparison_v3(question, evidence_context)
