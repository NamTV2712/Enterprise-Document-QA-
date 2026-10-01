"""Conservative, source-bound structured facts for optional answer visuals."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from src.generation.evidence_fact_renderer import (
    _NET_SALES_QUESTION_RE,
    _net_sales_value,
)
from src.retrieval.retriever import RetrievedChunk


_COMPANY_RE = re.compile(
    r"\bwhat\s+was\s+(?P<company>[A-Za-z][A-Za-z .&-]*?)"
    r"(?:'s|’s)\s+(?:total|consolidated)\s+net\s+sales\b",
    re.IGNORECASE,
)


def _evidence_quote(text: str, label: str, value: str) -> str | None:
    """Return one short line that contains both the printed metric and value."""
    for line in text.splitlines():
        normalized = " ".join(line.split())
        if label.casefold() in normalized.casefold() and value in normalized:
            return normalized[:500]
    return None


def build_visual_answer(
    question: str,
    chunks: list[RetrievedChunk],
) -> dict[str, Any] | None:
    """Build one directly printable net-sales metric or return ``None``.

    This intentionally supports no inferred units, periods, calculations, or
    cross-source joins. The frontend must treat a missing sidecar as the
    ordinary cited-prose path.
    """
    question_match = _NET_SALES_QUESTION_RE.search(question)
    company_match = _COMPANY_RE.search(question)
    if question_match is None or company_match is None:
        return None

    label = question_match.group("label")
    period = question_match.group("year")
    company = company_match.group("company").strip()
    for source_index, chunk in enumerate(chunks):
        # Do not infer a unit from another source: each rendered fact must be
        # independently inspectable from its own cited chunk.
        if not re.search(r"\b(?:in\s+millions|dollars\s+in\s+millions)\b", chunk.text, re.I):
            continue
        raw_value = _net_sales_value(chunk.text, label, period)
        if raw_value is None:
            continue
        try:
            numeric_value = Decimal(raw_value.replace(",", "").replace("$", ""))
        except InvalidOperation:
            continue
        quote = _evidence_quote(chunk.text, label, raw_value)
        if quote is None:
            # The table parser may use split rows. Without an exact local
            # quote, do not promote the value into a visual fact.
            continue
        return {
            "kind": "metric",
            "metric": "net_sales",
            "label": f"{company} {label.lower()}",
            "value": str(numeric_value),
            "display_value": f"${raw_value} million",
            "unit": "USD million",
            "period": period,
            "source_index": source_index,
            "source_chunk_id": chunk.chunk_id,
            "citation": chunk.citation,
            "evidence_quote": quote,
        }
    return None
