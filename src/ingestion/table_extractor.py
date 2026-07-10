"""
Module: table_extractor.py
Table-aware extraction for financial statement HTML tables.

Design principles based on real AAPL/MSFT/AMZN filing diagnostics:
1. Do not assume a fixed header row index; each filing can have a different
   number of title/spacer rows before the year header.
2. Remove empty spacer cells before mapping row values. SEC HTML tables often
   use empty cells to align currency signs and percentages visually.
3. Detect the header row by content, specifically rows containing multiple
   four-digit years.
"""

import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

YEAR_PATTERN = re.compile(r"(19|20)\d{2}")
STANDALONE_YEAR_PATTERN = re.compile(r"^(19|20)\d{2}$")
VALUE_PATTERN = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")
PERCENT_VALUE_PATTERN = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?%$")


@dataclass
class TableRow:
    label: str
    values_by_year: dict[str, str]


def _clean_cells(row: Tag) -> list[str]:
    """Return non-empty text from all table cells in one row."""
    cells = row.find_all(["td", "th"])
    texts = [cell.get_text(separator=" ", strip=True) for cell in cells]
    texts = [re.sub(r"\s+", " ", text).strip() for text in texts]
    return [text for text in texts if text]


def _extract_year_from_cell(cell_text: str) -> str | None:
    """Extract a four-digit year from a cell that may contain surrounding text."""
    match = YEAR_PATTERN.search(cell_text)
    return match.group(0) if match else None


def _find_header_row(rows: list[Tag]) -> tuple[int, list[str]] | None:
    """Find the first row containing at least two distinct year values."""
    for i, row in enumerate(rows):
        cleaned = _clean_cells(row)
        years_found = [year for year in (_extract_year_from_cell(cell) for cell in cleaned) if year]
        if len(set(years_found)) >= 2:
            return i, years_found
    return None


def _is_value_token(text: str) -> bool:
    """Return whether text looks like a numeric financial value."""
    return bool(VALUE_PATTERN.fullmatch(text))


def _is_section_header_row(cleaned_cells: list[str]) -> bool:
    """Return whether a row is a one-cell segment/section header."""
    if len(cleaned_cells) != 1:
        return False

    text = cleaned_cells[0]
    if text.endswith(":"):
        return False
    if YEAR_PATTERN.search(text):
        return False
    if re.fullmatch(r"[\$%\(\)\-\s]*", text):
        return False
    return True


def _extract_data_values(tokens: list[str], *, skip_percent_values: bool) -> list[str]:
    """Extract row values while handling currency and percentage tokens."""
    values = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        next_token = tokens[i + 1] if i + 1 < len(tokens) else ""

        if token in ("$", "%"):
            i += 1
            continue

        if token.startswith("$") and _is_value_token(token[1:]):
            values.append(token[1:])
            i += 1
            continue

        if PERCENT_VALUE_PATTERN.fullmatch(token):
            if not skip_percent_values:
                values.append(token)
            i += 1
            continue

        if _is_value_token(token) and next_token == "%" and skip_percent_values:
            i += 2
            continue

        if _is_value_token(token) and next_token == "%":
            values.append(f"{token}%")
            i += 2
            continue

        if token.startswith("(") and next_token == ")":
            values.append(f"{token})")
            i += 2
            continue

        if _is_value_token(token):
            values.append(token)

        i += 1
    return values


def extract_table_rows(table: Tag) -> list[TableRow]:
    """Parse one HTML table into structured metric-to-year values."""
    rows = table.find_all("tr")
    header_result = _find_header_row(rows)

    if header_result is None:
        logger.debug("No year header row found in table")
        return []

    header_idx, years = header_result
    header_cells = _clean_cells(rows[header_idx])
    skip_percent_values = any(cell.lower() == "change" for cell in header_cells)
    logger.debug("Header row index=%d, years=%s", header_idx, years)

    result: list[TableRow] = []
    current_segment: str | None = None
    for row in rows[header_idx + 1:]:
        cleaned = _clean_cells(row)
        if not cleaned:
            continue

        if _is_section_header_row(cleaned):
            current_segment = cleaned[0]
            logger.debug("Segment header detected: %s", current_segment)
            continue

        if len(cleaned) < 2:
            continue

        label = cleaned[0]
        if STANDALONE_YEAR_PATTERN.fullmatch(label) or label in ("$", "%") or label.endswith(":"):
            continue

        values = _extract_data_values(cleaned[1:], skip_percent_values=skip_percent_values)

        values_by_year = {}
        for year, value in zip(years, values):
            values_by_year[year] = value

        if values_by_year:
            full_label = f"{current_segment} - {label}" if current_segment else label
            result.append(TableRow(label=full_label, values_by_year=values_by_year))

    return result


def find_table_containing_text(soup: BeautifulSoup, anchor_text: str) -> Tag | None:
    """Find the nearest parent table containing the given text anchor."""
    node = soup.find(string=lambda text: text and anchor_text in text)
    if node is None:
        return None

    parent = node.parent
    while parent is not None:
        if parent.name == "table":
            return parent
        parent = parent.parent
    return None


def get_table_caption(table: Tag, max_chars: int = 150) -> str:
    """Find a nearby caption by scanning meaningful text nodes before a table."""
    texts_found = []
    node = table.find_previous(string=True)
    steps = 0
    while node is not None and steps < 15:
        text = re.sub(r"\s+", " ", node.strip()).strip()
        if text and len(text) > 10:
            texts_found.append(text)
            if len(texts_found) >= 2:
                break
        node = node.find_previous(string=True)
        steps += 1

    if not texts_found:
        return "(no caption found)"

    caption = " ".join(reversed(texts_found))
    return caption[:max_chars]


def rows_to_markdown(rows: list[TableRow], table_name: str = "") -> str:
    """Convert structured table rows to markdown for readable embedding text."""
    if not rows:
        return ""

    all_years = sorted({year for row in rows for year in row.values_by_year}, reverse=True)
    lines = []
    if table_name:
        lines.append(f"### {table_name}")
    lines.append("| Metric | " + " | ".join(all_years) + " |")
    lines.append("|---" * (len(all_years) + 1) + "|")
    for row in rows:
        row_values = [row.values_by_year.get(year, "-") for year in all_years]
        lines.append(f"| {row.label} | " + " | ".join(row_values) + " |")
    return "\n".join(lines)
