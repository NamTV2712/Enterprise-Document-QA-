"""Structured lookup for high-precision filing evidence retrieval.

This module handles questions where lexical row identity matters more than
semantic similarity, such as "total assets" vs. "long-lived assets". It uses
the existing extracted chunks, so no data regeneration is needed.
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
        "commitments and contingencies - total stockholders' equity",
        "commitments and contingencies - total shareholders' equity",
    ],
}

AUDITOR_SIGNATURE_KEY = "auditor signature"
CONSOLIDATED_CAPTION_MARKERS = (
    "consolidated balance sheet",
    "consolidated balance sheets",
    "consolidated statement",
    "consolidated statements",
)


@dataclass(frozen=True)
class StructuredMatch:
    chunk: dict
    canonical_key: str
    label: str
    line: str


def detect_structured_query(question: str) -> str | None:
    """Return the canonical evidence type requested by a question, if any."""
    normalized = question.lower()
    if _is_auditor_query(normalized):
        return AUDITOR_SIGNATURE_KEY
    for key in CANONICAL_LABELS:
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return key
    return None


def _is_auditor_query(normalized_question: str) -> bool:
    asks_about_auditor = re.search(r"\b(auditor|audited|accounting firm|report signed)\b", normalized_question)
    asks_about_filing_report = re.search(r"\b(financial statements|report signed|audit report)\b", normalized_question)
    return bool(asks_about_auditor and asks_about_filing_report)


def _normalize_label(label: str) -> str:
    label = _normalize_quotes(label)
    label = label.lower().strip()
    label = re.sub(r"\s+", " ", label)
    label = re.sub(r"\s*\([^)]*\)", "", label)
    return label.strip(" .:-")


def _normalize_quotes(text: str) -> str:
    """Normalize SEC smart quotes before comparing table labels.

    SEC filings commonly encode apostrophes as HTML entity 8217, which becomes
    U+2019 after extraction. This is valid data, but canonical labels in code
    use ASCII apostrophes, so matching should normalize both sides.
    """
    return text.replace("\u2019", "'").replace("\u2018", "'")


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


def _caption_text(chunk: dict) -> str:
    """Return the markdown table caption/header text for match prioritization."""
    text = chunk.get("text", "")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("###"):
            return stripped.lstrip("#").strip()
        if stripped.startswith("|"):
            break
    return ""


def _pick_best_table_match(candidates: list[StructuredMatch]) -> StructuredMatch | None:
    """Prefer consolidated company-level tables when duplicate total rows exist."""
    if not candidates:
        return None

    for candidate in candidates:
        caption = _caption_text(candidate.chunk).lower()
        if any(marker in caption for marker in CONSOLIDATED_CAPTION_MARKERS):
            return candidate
    return candidates[0]


def _contains_auditor_signature(text: str) -> bool:
    normalized = _normalize_quotes(text).lower()
    compact = re.sub(r"\s+", " ", normalized)
    return "/s/" in normalized and re.search(r"served as .* auditor since", compact) is not None


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

    if canonical_key == AUDITOR_SIGNATURE_KEY:
        for chunk in all_chunks:
            if chunk.get("ticker") != ticker or chunk.get("section") != "financial_statements":
                continue
            if _contains_auditor_signature(chunk.get("text", "")):
                return StructuredMatch(
                    chunk=chunk,
                    canonical_key=canonical_key,
                    label=AUDITOR_SIGNATURE_KEY,
                    line="auditor signature",
                )
        return None

    variants = CANONICAL_LABELS[canonical_key]
    candidates: list[StructuredMatch] = []
    for chunk in all_chunks:
        if chunk.get("ticker") != ticker or chunk.get("section") != "financial_table":
            continue
        for row_label, line in _iter_markdown_rows(chunk.get("text", "")):
            if _label_matches_canonical(row_label, variants):
                candidates.append(
                    StructuredMatch(
                        chunk=chunk,
                        canonical_key=canonical_key,
                        label=row_label,
                        line=line,
                    )
                )
    return _pick_best_table_match(candidates)
