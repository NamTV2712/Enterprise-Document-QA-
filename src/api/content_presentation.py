"""Strict presentation metadata for indexed financial-table chunks."""
from __future__ import annotations

import re
from typing import Any

_YEAR = re.compile(r"^(?:19|20)\d{2}$")
_SEPARATOR = re.compile(r"^:?-{3,}:?$")


def _split_row(line: str) -> list[str] | None:
    value = line.strip()
    if not value.startswith("|") or not value.endswith("|"):
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in value[1:-1]:
        if escaped:
            current.extend(("|",) if character == "|" else ("\\", character))
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def parse_indexed_markdown_table(
    text: str,
    *,
    max_rows: int = 1000,
    max_columns: int = 32,
) -> dict[str, Any] | None:
    """Return a lossless table DTO, or ``None`` for ambiguous text."""
    if not text or len(text) > 2_000_000:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return None
    caption: str | None = None
    units: str | None = None
    cursor = 0
    if lines[cursor].startswith("### "):
        caption = lines[cursor][4:].strip()
        if not caption:
            return None
        cursor += 1
    if cursor < len(lines) and lines[cursor].startswith("Units: "):
        units = lines[cursor][7:].strip()
        if not units:
            return None
        cursor += 1
    if cursor + 2 > len(lines):
        return None
    header = _split_row(lines[cursor])
    separator = _split_row(lines[cursor + 1])
    if header is None or separator is None or len(header) < 3 or len(header) > max_columns:
        return None
    if header[0].casefold() != "metric" or not all(_YEAR.fullmatch(cell) for cell in header[1:]):
        return None
    if len(set(header[1:])) != len(header) - 1 or len(separator) != len(header):
        return None
    if not all(_SEPARATOR.fullmatch(cell) for cell in separator):
        return None
    rows: list[list[str]] = []
    for line in lines[cursor + 2 :]:
        row = _split_row(line)
        if row is None or len(row) != len(header):
            return None
        rows.append(row)
        if len(rows) > max_rows:
            return None
    return {"kind": "markdown_table", "caption": caption, "units": units, "columns": header, "rows": rows}


def build_chunk_presentation(text: str, section: str | None) -> dict[str, Any]:
    """Build safe presentation metadata for one complete indexed chunk."""
    if section != "financial_table":
        return {"kind": "plain_text", "reason": "not_financial_table"}
    table = parse_indexed_markdown_table(text)
    return table or {"kind": "plain_text", "reason": "unsupported_or_ambiguous_table"}
