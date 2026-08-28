"""Production financial-table discovery with a conservative TOC-link fallback."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from scripts.diagnostics.diagnose_all_financial_tables import find_tables_in_financial_section
from src.ingestion.table_extractor import extract_table_rows

_STATEMENT_LINK = re.compile(r"consolidated|balance sheets?|statements? of|cash flows?", re.I)
_ROOT_FINANCIAL_ANCHOR = re.compile(r"^financial statements(?: and supplementary data)?$", re.I)
_STATEMENT_ROW = re.compile(
    r"revenue|net sales|income|assets|liabilit|cash flow|equity|operating profit",
    re.I,
)
SAME_DOCUMENT_INTERVAL_TICKERS = frozenset({"CVX", "JPM", "XOM"})
_INTERVAL_START_LABELS = (
    (0, re.compile(r"^consolidated statements? of (income|operations|earnings)", re.I)),
    (1, re.compile(r"^consolidated financial statements$", re.I)),
    (2, re.compile(r"^(consolidated )?(balance sheet|statement of cash flows?)$", re.I)),
)
_INTERVAL_STOP = re.compile(
    r"^(?:notes to (?:the )?consolidated financial statements|item\s+9\b|"
    r"part\s+(?:iii|iv)\b|signatures?\b)",
    re.I,
)


def _node_positions(soup: BeautifulSoup) -> dict[int, int]:
    return {id(node): index for index, node in enumerate(soup.descendants)}


def _normalized_text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _table_fingerprint(table: Tag) -> str:
    text = _normalized_text(table).encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _same_document_interval_starts(
    soup: BeautifulSoup,
    positions: dict[int, int],
) -> list[dict[str, Any]]:
    """Return deterministic candidates for a same-document statement interval."""
    candidates: list[dict[str, Any]] = []
    seen_positions: set[int] = set()
    for link in soup.find_all("a", href=True):
        label = _normalized_text(link)
        rank = next(
            (rank for rank, pattern in _INTERVAL_START_LABELS if pattern.fullmatch(label)),
            None,
        )
        href = str(link["href"])
        if rank is None or not href.startswith("#") or len(href) == 1:
            continue
        target = soup.find(id=href[1:]) or soup.find(attrs={"name": href[1:]})
        if not isinstance(target, Tag):
            continue
        position = positions.get(id(target))
        if position is None or position in seen_positions:
            continue
        seen_positions.add(position)
        candidates.append({"rank": rank, "position": position, "target": target})
    return sorted(candidates, key=lambda item: (item["rank"], item["position"]))


def _same_document_interval_stop(
    soup: BeautifulSoup,
    start: Tag,
    positions: dict[int, int],
) -> Tag | None:
    start_position = positions[id(start)]
    candidates: list[tuple[int, Tag]] = []
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span"]):
        position = positions.get(id(node), -1)
        text = _normalized_text(node)
        if position > start_position and len(text) <= 240 and _INTERVAL_STOP.match(text):
            candidates.append((position, node))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def discover_same_document_interval_tables(html_path: Path) -> list[Tag]:
    """Return unique parseable tables from one bounded statement interval.

    This generic resolver is deliberately activated only for the three filings
    whose read-only counterfactual proved a clean same-document route. It does
    not repair section text; it supplies supplemental table chunks only.
    """
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    positions = _node_positions(soup)
    candidates = _same_document_interval_starts(soup, positions)
    if not candidates:
        return []
    start = candidates[0]["target"]
    stop = _same_document_interval_stop(soup, start, positions)
    if stop is None:
        return []

    low = positions[id(start)]
    high = positions[id(stop)]
    tables: list[Tag] = []
    seen: set[str] = set()
    for table in soup.find_all("table"):
        position = positions.get(id(table), -1)
        if not low < position < high or not extract_table_rows(table):
            continue
        fingerprint = _table_fingerprint(table)
        if fingerprint not in seen:
            seen.add(fingerprint)
            tables.append(table)
    return tables

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


def discover_root_anchor_tables(html_path: Path) -> list[Tag]:
    """Recover statement tables preceding a root Financial Statements anchor.

    Some filings (notably PEP) expose a root TOC link and place the actual
    statement tables earlier in DOM order, without individual statement hrefs.
    This fallback only considers tables before that anchor, requires parsed
    multi-year rows with statement-like labels, and fingerprints table text to
    avoid duplicate chunks.
    """
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    anchors = [
        link for link in soup.find_all("a", href=True)
        if _ROOT_FINANCIAL_ANCHOR.fullmatch(" ".join(link.get_text(" ", strip=True).split()))
        and str(link["href"]).startswith("#")
    ]
    if not anchors:
        return []
    target_id = str(anchors[0]["href"])[1:]
    target = soup.find(id=target_id) or soup.find(attrs={"name": target_id})
    if not isinstance(target, Tag):
        return []

    all_nodes = list(soup.find_all(True))
    try:
        target_pos = all_nodes.index(target)
    except ValueError:
        return []
    tables: list[Tag] = []
    seen: set[str] = set()
    for table in soup.find_all("table"):
        try:
            if all_nodes.index(table) >= target_pos:
                break
        except ValueError:
            continue
        rows = extract_table_rows(table)
        if len({year for row in rows for year in row.values_by_year}) < 2:
            continue
        if not any(_STATEMENT_ROW.search(row.label) for row in rows):
            continue
        fingerprint = " ".join(table.get_text(" ", strip=True).split())
        if fingerprint and fingerprint not in seen:
            seen.add(fingerprint)
            tables.append(table)
    return tables

def discover_financial_tables(html_path: Path, sections_path: Path) -> tuple[list[Tag], str]:
    """Return primary tables, or statement-link fallback when primary is empty."""
    filing = json.loads(sections_path.read_text(encoding="utf-8"))
    has_financial_statements = "financial_statements" in filing.get("sections", {})
    if has_financial_statements:
        primary = find_tables_in_financial_section(html_path, sections_path)
        if any(extract_table_rows(table) for table in primary):
            return primary, "item8_interval"

    ticker = str(filing.get("ticker", "")).upper()
    if ticker in SAME_DOCUMENT_INTERVAL_TICKERS:
        same_document = discover_same_document_interval_tables(html_path)
        if same_document:
            return same_document, "same_document_statement_interval"

    fallback = discover_statement_link_tables(html_path)
    if not fallback:
        fallback = discover_root_anchor_tables(html_path)
    return fallback, "statement_toc_links" if fallback else "item8_interval_empty"
