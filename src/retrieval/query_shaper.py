"""Deterministic retrieval hints shared by direct and decomposed queries.

The query shaper does not rewrite the user's question and never changes the
question sent to generation. It only adds filing-native terms to the retrieval
query when the original wording describes a derived financial concept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
import hashlib
import json


QUERY_SHAPER_VERSION = 1


TREND_TERMS = (
    "growth",
    "trend",
    "change",
    "changed",
    "year over year",
    "year-over-year",
    "yoy",
)


def _fingerprint() -> str:
    """Return provenance for every rule that can change retrieval output."""
    payload = {
        "version": QUERY_SHAPER_VERSION,
        "trend_terms": TREND_TERMS,
        "rules": {
            "aws_trend": {
                "requires": ["aws", "trend_term"],
                "exact_phrases": ["AWS net sales"],
                "full_terms": ["AWS", "net", "sales"],
                "additions": ["AWS", "net sales"],
                "implicit_years": ["2025", "2024"],
            }
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


QUERY_SHAPER_FINGERPRINT = _fingerprint()


@dataclass(frozen=True)
class ShapedQuery:
    original: str
    retrieval_query: str
    exact_phrases: tuple[str, ...] = ()
    full_terms: tuple[str, ...] = ()


def _has_trend_intent(query: str) -> bool:
    normalized = query.casefold()
    return any(term in normalized for term in TREND_TERMS)


def shape_retrieval_query(query: str) -> ShapedQuery:
    """Add conservative table vocabulary for known derived-metric wording."""
    normalized = query.casefold()
    additions: list[str] = []
    exact_phrases: list[str] = []
    full_terms: list[str] = []

    # Amazon filings label the underlying revenue row ``AWS - Net sales``;
    # semantic wording such as ``AWS growth`` otherwise lands on operating
    # income or generic AWS discussion. Keep this rule entity/metric scoped.
    if "aws" in normalized and _has_trend_intent(query):
        exact_phrases.append("AWS net sales")
        full_terms.extend(("AWS", "net", "sales"))
        if not re.search(r"\b20\d{2}\b", query):
            additions.extend(("2025", "2024"))
        additions.extend(("AWS", "net sales"))

    if not additions:
        return ShapedQuery(
            original=query,
            retrieval_query=query,
            exact_phrases=tuple(exact_phrases),
            full_terms=tuple(full_terms),
        )

    return ShapedQuery(
        original=query,
        retrieval_query=f"{query} {' '.join(additions)}",
        exact_phrases=tuple(exact_phrases),
        full_terms=tuple(full_terms),
    )
