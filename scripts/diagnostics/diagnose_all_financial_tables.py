"""
Diagnose parser coverage across all financial statement tables.

Run from the project root:
    python -m scripts.diagnostics.diagnose_all_financial_tables

This script is intentionally read-only. It does not modify processed chunks or
the retrieval index.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

from src.ingestion.table_extractor import extract_table_rows, get_table_caption


FILINGS = [
    (
        "AAPL",
        Path("data/raw/AAPL/000032019325000079.html"),
        Path("data/processed/AAPL/000032019325000079_sections.json"),
    ),
    (
        "MSFT",
        Path("data/raw/MSFT/000095017025100235.html"),
        Path("data/processed/MSFT/000095017025100235_sections.json"),
    ),
    (
        "AMZN",
        Path("data/raw/AMZN/000101872426000004.html"),
        Path("data/processed/AMZN/000101872426000004_sections.json"),
    ),
]


def _candidate_start_snippets(financial_statement_text: str) -> list[str]:
    """Return candidate raw-text anchors from the extracted section start."""
    snippets = []
    normalized = financial_statement_text.strip()
    if normalized:
        snippets.append(normalized[:40].strip())

    for line in normalized.splitlines()[:20]:
        line = line.strip()
        if len(line) >= 12:
            snippets.append(line[:80])

    seen = set()
    return [snippet for snippet in snippets if snippet and not (snippet in seen or seen.add(snippet))]


def _find_start_node(soup: BeautifulSoup, financial_statement_text: str) -> NavigableString | None:
    """Find a DOM text node near the start of the extracted financial section."""
    for snippet in _candidate_start_snippets(financial_statement_text):
        node = soup.find(string=lambda text: text and snippet in text)
        if node is not None:
            return node
    return None


def _resolve_toc_link_start(soup: BeautifulSoup, start_node: NavigableString) -> Tag | NavigableString:
    """Follow an internal TOC link when the matched anchor is inside one."""
    parent = start_node.parent
    while parent is not None:
        if parent.name == "a" and parent.get("href", "").startswith("#"):
            target_id = parent["href"][1:]
            target = soup.find(id=target_id) or soup.find(attrs={"name": target_id})
            if target is not None:
                return target
            return start_node
        parent = parent.parent
    return start_node


def find_tables_in_financial_section(html_path: Path, sections_json_path: Path) -> list[Tag]:
    """
    Locate all tables in the financial statements section using the verified
    extracted section text as the DOM anchor.
    """
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    sections = json.loads(sections_json_path.read_text(encoding="utf-8"))
    financial_statement_text = sections["sections"]["financial_statements"]
    start_node = _find_start_node(soup, financial_statement_text)

    if start_node is None:
        first_snippet = financial_statement_text[:40].strip()
        print(f"WARNING: could not find financial section start anchor {first_snippet!r}")
        return []

    start = _resolve_toc_link_start(soup, start_node)
    tables = []
    item_9_pattern = re.compile(r"item\s+9\b", re.IGNORECASE)
    for elem in start.next_elements:
        if isinstance(elem, NavigableString) and item_9_pattern.search(str(elem)):
            break
        if isinstance(elem, Tag) and elem.name == "table":
            tables.append(elem)
    return tables


def main() -> None:
    for ticker, html_path, sections_json_path in FILINGS:
        print(f"\n{'=' * 50}\n{ticker}\n{'=' * 50}")

        if not html_path.exists():
            print(f"Missing raw filing: {html_path}")
            continue
        if not sections_json_path.exists():
            print(f"Missing sections JSON: {sections_json_path}")
            continue

        tables = find_tables_in_financial_section(html_path, sections_json_path)
        print(f"Total <table> in financial_statements: {len(tables)}")

        parsed_ok = 0
        parsed_empty = 0
        parsed_rows_by_table = []
        for table in tables:
            rows = extract_table_rows(table)
            parsed_rows_by_table.append(rows)
            if rows:
                parsed_ok += 1
            else:
                parsed_empty += 1

        print(f"Parsed OK (has rows): {parsed_ok}")
        print(f"Parsed empty (no year header): {parsed_empty}")

        print("\n--- Caption and label preview of first 15 parsed tables ---")
        shown = 0
        for table, rows in zip(tables, parsed_rows_by_table):
            if shown >= 15:
                break
            if not rows:
                continue
            caption = get_table_caption(table)
            labels = [row.label for row in rows[:3]]
            print(f"  [{caption[:80]}] -> {labels}")
            shown += 1


if __name__ == "__main__":
    main()
