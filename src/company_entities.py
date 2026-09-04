"""Shared company alias and ticker detection helpers."""

from __future__ import annotations

import re


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


def detect_tickers(question: str) -> tuple[str, ...]:
    """Return recognized tickers in their first appearance order."""
    normalized = question.casefold()
    positions: dict[str, int] = {}
    uppercase_tokens = set(re.findall(r"\b[A-Z]{1,5}(?:-[A-Z])?\b", question))
    for ticker, aliases in COMPANY_ALIASES.items():
        for alias in aliases:
            match = re.search(rf"\b{re.escape(alias)}\b", normalized)
            if match is not None:
                positions[ticker] = min(
                    positions.get(ticker, match.start()), match.start()
                )
        if ticker in uppercase_tokens:
            positions[ticker] = min(
                positions.get(ticker, len(question)), question.find(ticker)
            )
    return tuple(
        ticker
        for ticker, _ in sorted(
            positions.items(), key=lambda item: (item[1], item[0])
        )
    )
