"""Structured lookup for high-precision financial table row retrieval.

This module handles questions where lexical row identity matters more than
semantic similarity, such as "total assets" vs. "long-lived assets". It uses
the existing rendered markdown table chunks, so no data regeneration is needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


CANONICAL_LABELS: dict[str, list[str]] = {
    "total assets": ["assets - total assets", "total assets"],
    "total liabilities": ["liabilities - total liabilities", "total liabilities"],
    "total revenue": ["total revenue", "total net sales", "net sales - total net sales"],
    "total equity": [
        "stockholders' equity - total stockholders' equity",
        "shareholders' equity - total shareholders' equity",
        "total stockholders' equity",
        "total shareholders' equity",
        "total equity",
    ],
}


@dataclass(frozen=True)
class StructuredMatch:
    chunk: dict
    canonical_key: str
    label: str
    line: str


def detect_structured_query(question: str) -> str | None:
    """Return the canonical financial row requested by a question, if any."""
    normalized = question.lower()
    for key in CANONICAL_LABELS:
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return key
    return None


def _normalize_label(label: str) -> str:
    label = label.lower().strip()
    label = re.sub(r"\s+", " ", label)
    return label.strip(" .:-")


def _label_matches_canonical(label: str, canonical_variants: list[str]) -> bool:
    """Match exact row labels only, avoiding subtotal false positives."""
    normalized = _normalize_label(label)
    for variant in canonical_variants:
        normalized_variant = _normalize_label(variant)
        if normalized == normalized_variant:
            return True
        if normalized_variant.startswith("total ") and normalized.endswith(f" - {normalized_variant}"):
            return True
    return False


def _iter_markdown_rows(text: str):
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() != "metric":
            yield cells[0], stripped


def structured_lookup(
    question: str,
    ticker: str | None,
    all_chunks: list[dict],
) -> StructuredMatch | None:
    """Find an exact financial table row match for confident total-X queries."""
    if ticker is None:
        return None

    canonical_key = detect_structured_query(question)
    if canonical_key is None:
        return None

    variants = CANONICAL_LABELS[canonical_key]
    for chunk in all_chunks:
        if chunk.get("ticker") != ticker or chunk.get("section") != "financial_table":
            continue
        for row_label, line in _iter_markdown_rows(chunk.get("text", "")):
            if _label_matches_canonical(row_label, variants):
                return StructuredMatch(
                    chunk=chunk,
                    canonical_key=canonical_key,
                    label=row_label,
                    line=line,
                )
    return None
