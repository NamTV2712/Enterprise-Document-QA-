"""Deterministic company scoping and narrow Vietnamese retrieval translation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from src.company_entities import COMPANY_ALIASES, detect_tickers
VIETNAMESE_METRICS = {
    "doanh thu": "total revenue",
    "doanh số": "total revenue",
    "rủi ro": "risk factors",
    "tài sản": "total assets",
    "lợi nhuận": "net income",
    "tăng trưởng": "growth",
    "tỷ lệ": "share",
    "thị phần": "market share",
    "dịch vụ": "services",
    "đám mây": "cloud",
    "dòng tiền": "cash flow",
    "nợ phải trả": "total liabilities",
    "vốn chủ sở hữu": "total equity",
}
VIETNAMESE_MARKERS = tuple(VIETNAMESE_METRICS)
VIETNAMESE_QUERY_TERMS = {
    "so sánh": "compare",
    "giữa": "between",
    "và": "and",
    "năm tài chính": "fiscal year",
    "năm": "year",
    "quốc tế": "international",
    "kinh doanh": "business",
    "chính": "primary",
    "chính yếu": "primary",
    "mới nhất": "latest",
}


def _fold_vietnamese(value: str) -> str:
    folded = unicodedata.normalize("NFD", value.casefold())
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    return folded.replace("đ", "d")


@dataclass(frozen=True)
class NormalizedQuery:
    question: str
    detected_ticker: str | None
    translated_from_vietnamese: bool
    translation_method: str = "unchanged"


def detect_ticker(question: str) -> str | None:
    """Return a single unambiguous ticker inferred from a query, if present."""
    matches = detect_tickers(question)
    return matches[0] if len(matches) == 1 else None


def normalize_retrieval_question(question: str) -> NormalizedQuery:
    """Translate supported Vietnamese financial intents into safe English retrieval text.

    This intentionally handles only explicit, high-confidence metric phrases.
    Other Vietnamese questions are left unchanged rather than mistranslated.
    """
    ticker = detect_ticker(question)
    normalized = question.casefold()
    folded = _fold_vietnamese(question)
    matched_metrics = [
        (vietnamese, english)
        for vietnamese, english in VIETNAMESE_METRICS.items()
        if vietnamese in normalized or _fold_vietnamese(vietnamese) in folded
    ]
    metric = next(
        (english for _, english in matched_metrics),
        None,
    )
    if metric is None:
        return NormalizedQuery(question, ticker, False, "unchanged")

    company = next(
        (
            alias.title()
            for candidate_ticker, aliases in COMPANY_ALIASES.items()
            if candidate_ticker == ticker
            for alias in aliases
        ),
        "the company",
    )
    comparative = any(
        marker in normalized or marker in folded
        for marker in ("so sánh", "giữa", "và", "compare", "versus", " vs ")
    )
    year = re.search(r"\b20\d{2}\b", question)
    if comparative or len(matched_metrics) > 1 or ticker is None:
        # Preserve complex intent and all explicit entities. Add only high
        # confidence English retrieval hints; never collapse a comparison or
        # multi-metric question into a single synthetic sentence.
        hints = [english for _, english in matched_metrics]
        translated = question
        for vietnamese, english in (
            *VIETNAMESE_QUERY_TERMS.items(),
            *VIETNAMESE_METRICS.items(),
        ):
            folded_term = _fold_vietnamese(vietnamese)
            pattern = re.compile(
                rf"{re.escape(vietnamese)}|{re.escape(folded_term)}",
                flags=re.IGNORECASE,
            )
            translated = pattern.sub(english, translated)
        translated = f"{translated} ({', '.join(dict.fromkeys(hints))})"
        return NormalizedQuery(translated, ticker, True, "lexical_hints")

    translated = f"What was {company}'s {metric}"
    if year:
        translated += f" in {year.group()}"
    translated += "?"
    return NormalizedQuery(translated, ticker, True, "deterministic_rule")
