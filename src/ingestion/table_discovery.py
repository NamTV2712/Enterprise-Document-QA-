"""Production financial-table discovery with a conservative TOC-link fallback."""
from __future__ import annotations

import re
from pathlib import Path
from bs4 import BeautifulSoup, Tag

from scripts.diagnostics.diagnose_all_financial_tables import find_tables_in_financial_section
from src.ingestion.table_extractor import extract_table_rows

_STATEMENT_LINK = re.compile(r"consolidated|balance sheets?|statements? of|cash flows?", re.I)

def _resolve_body_target(soup: BeautifulSoup, target: Tag) -> Tag:
    if target.get_text(" ", strip=True):
        return target
    for node in target.next_elements:
        if isinstance(node, str) and re.search(r"\bitem\s+8\b", node, re.I):
            return node.parent if isinstance(node.parent, Tag) else target
    return target

def discover_statement_link_tables(html_path: Path) -> list[Tag]:
    """Follow individual statement TOC links and return unique parseable tables."""
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    tables: list[Tag] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        if not _STATEMENT_LINK.search(label) or not str(link["href"]).startswith("#"):
            continue
        key = str(link["href"])[1:]
        target = soup.find(id=key) or soup.find(attrs={"name": key})
        if not isinstance(target, Tag):
            continue
        start = _resolve_body_target(soup, target)
        for table in start.find_all_next("table"):
            if not extract_table_rows(table):
                continue
            fingerprint = " ".join(table.get_text(" ", strip=True).split())
            if fingerprint not in seen:
                seen.add(fingerprint)
                tables.append(table)
            break
    return tables

def discover_financial_tables(html_path: Path, sections_path: Path) -> tuple[list[Tag], str]:
    """Return primary tables, or statement-link fallback when primary is empty."""
    primary = find_tables_in_financial_section(html_path, sections_path)
    if any(extract_table_rows(table) for table in primary):
        return primary, "item8_interval"
    fallback = discover_statement_link_tables(html_path)
    return fallback, "statement_toc_links" if fallback else "item8_interval_empty"
