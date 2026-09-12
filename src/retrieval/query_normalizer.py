"""Deterministic company scoping and narrow Vietnamese retrieval translation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from src.company_entities import COMPANY_ALIASES, detect_tickers
VIETNAMESE_METRICS = {
    "doanh thu": "total revenue",
    "doanh số": "total revenue",
    "lợi nhuận gộp": "gross profit",
    "lợi nhuận hoạt động": "operating income",
    "lợi nhuận ròng": "net income",
    "lợi nhuận sau thuế": "net income",
    "lợi nhuận": "profit",
    "rủi ro": "risk factors",
    "tài sản": "total assets",
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
    requested_periods: tuple[str, ...] = ()
    is_comparative: bool = False


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
    matched_metrics = _matched_metric_terms(folded)
    requested_periods = tuple(dict.fromkeys(re.findall(r"\b(?:19|20)\d{2}\b", question)))
    metric = next(
        (english for _, english in matched_metrics),
        None,
    )
    if metric is None:
        return NormalizedQuery(question, ticker, False, "unchanged", requested_periods)

    company = next(
        (
            alias.title()
            for candidate_ticker, aliases in COMPANY_ALIASES.items()
            if candidate_ticker == ticker
            for alias in aliases
        ),
        "the company",
    )
    comparative = _contains_comparison_signal(normalized, folded) or len(requested_periods) > 1
    year = requested_periods[0] if requested_periods else None
    if comparative or len(matched_metrics) > 1 or ticker is None:
        # Preserve complex intent and all explicit entities. Add only high
        # confidence English retrieval hints; never collapse a comparison or
        # multi-metric question into a single synthetic sentence.
        hints = [english for _, english in matched_metrics]
        translated = question
        for vietnamese, english in _translation_terms():
            folded_term = _fold_vietnamese(vietnamese)
            pattern = re.compile(
                rf"(?<!\w)(?:{re.escape(vietnamese)}|{re.escape(folded_term)})(?!\w)",
                flags=re.IGNORECASE,
            )
            translated = pattern.sub(english, translated)
        translated = f"{translated} ({', '.join(dict.fromkeys(hints))})"
        return NormalizedQuery(
            translated,
            ticker,
            True,
            "lexical_hints",
            requested_periods,
            comparative,
        )

    translated = f"What was {company}'s {metric}"
    if year:
        translated += f" in {year}"
    translated += "?"
    return NormalizedQuery(
        translated,
        ticker,
        True,
        "deterministic_rule",
        requested_periods,
        comparative,
    )


def _matched_metric_terms(folded_question: str) -> list[tuple[str, str]]:
    """Return longest non-overlapping metric phrases from a folded question."""
    candidates: list[tuple[int, int, str, str]] = []
    for vietnamese, english in VIETNAMESE_METRICS.items():
        term = _fold_vietnamese(vietnamese)
        for match in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", folded_question):
            candidates.append((match.start(), match.end(), vietnamese, english))

    selected: list[tuple[int, int, str, str]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(candidate[0] < chosen[1] and chosen[0] < candidate[1] for chosen in selected):
            continue
        selected.append(candidate)
    return [(vietnamese, english) for _, _, vietnamese, english in sorted(selected)]


def _translation_terms() -> list[tuple[str, str]]:
    """Prefer longer phrases so generic terms cannot rewrite their prefixes."""
    return sorted(
        (*VIETNAMESE_QUERY_TERMS.items(), *VIETNAMESE_METRICS.items()),
        key=lambda item: len(_fold_vietnamese(item[0])),
        reverse=True,
    )


def _contains_comparison_signal(normalized: str, folded: str) -> bool:
    """Detect comparison/change intent without treating every conjunction as one."""
    signals = (
        "so sánh",
        "so sanh",
        "compare",
        "versus",
        " vs ",
        "giữa",
        "giua",
        "từ",
        "tu",
        "đến",
        "den",
        "thay đổi",
        "thay doi",
        "qua các năm",
        "qua cac nam",
        "tăng trưởng",
        "tang truong",
    )
    return any(signal in normalized or signal in folded for signal in signals)
