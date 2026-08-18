"""Deterministic company scoping and narrow Vietnamese retrieval translation."""

from __future__ import annotations

import re
from dataclasses import dataclass


COMPANY_ALIASES = {
    "AAPL": ("apple",),
    "MSFT": ("microsoft",),
    "AMZN": ("amazon",),
    "GOOGL": ("alphabet", "google"),
    "META": ("meta", "facebook"),
    "NVDA": ("nvidia",),
    "TSLA": ("tesla",),
    "MS": ("morgan stanley",),
    "MCD": ("mcdonald's", "mcdonalds"),
    "INTC": ("intel",),
    "COST": ("costco",),
    "GE": ("general electric", "ge aerospace"),
    "HON": ("honeywell",),
}
VIETNAMESE_METRICS = {
    "doanh thu": "total revenue",
    "rủi ro": "risk factors",
    "tài sản": "total assets",
    "lợi nhuận": "net income",
}
VIETNAMESE_MARKERS = tuple(VIETNAMESE_METRICS)


@dataclass(frozen=True)
class NormalizedQuery:
    question: str
    detected_ticker: str | None
    translated_from_vietnamese: bool


def detect_ticker(question: str) -> str | None:
    """Return a single unambiguous ticker inferred from a query, if present."""
    normalized = question.casefold()
    matches = {
        ticker
        for ticker, aliases in COMPANY_ALIASES.items()
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases)
    }
    uppercase_tokens = set(re.findall(r"\b[A-Z]{1,5}(?:-[A-Z])?\b", question))
    matches.update(ticker for ticker in COMPANY_ALIASES if ticker in uppercase_tokens)
    return next(iter(matches)) if len(matches) == 1 else None


def normalize_retrieval_question(question: str) -> NormalizedQuery:
    """Translate supported Vietnamese financial intents into safe English retrieval text.

    This intentionally handles only explicit, high-confidence metric phrases.
    Other Vietnamese questions are left unchanged rather than mistranslated.
    """
    ticker = detect_ticker(question)
    normalized = question.casefold()
    metric = next(
        (english for vietnamese, english in VIETNAMESE_METRICS.items() if vietnamese in normalized),
        None,
    )
    if metric is None:
        return NormalizedQuery(question, ticker, False)

    company = next(
        (
            alias.title()
            for candidate_ticker, aliases in COMPANY_ALIASES.items()
            if candidate_ticker == ticker
            for alias in aliases
        ),
        "the company",
    )
    year = re.search(r"\b20\d{2}\b", question)
    translated = f"What was {company}'s {metric}"
    if year:
        translated += f" in {year.group()}"
    translated += "?"
    return NormalizedQuery(translated, ticker, True)
