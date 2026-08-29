"""Conservative resolver for financial tables in incorporated companion filings."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.ingestion.table_extractor import extract_table_rows

_COMPANION_LABEL = re.compile(r"annual report to (?:stockholders|security holders)", re.I)
_PAGE_RANGE = re.compile(r"item\s+8\b.{0,700}?pages?\s+(\d+)\s+(?:through|to|-)\s+(\d+)", re.I)
_STATEMENT_LABEL = re.compile(
    r"revenue|net sales|income|assets|liabilit|cash flow|equity|operating profit",
    re.I,
)


def _normalize(value: str) -> str:
    return " ".join(value.split())


def _positions(soup: BeautifulSoup) -> dict[int, int]:
    return {id(node): index for index, node in enumerate(soup.descendants)}


def extract_companion_page_range(primary_html: Path) -> tuple[int, int] | None:
    text = _normalize(BeautifulSoup(primary_html.read_bytes(), "lxml").get_text(" ", strip=True))
    match = _PAGE_RANGE.search(text)
    return (int(match.group(1)), int(match.group(2))) if match else None


def discover_companion_candidates(primary_html: Path) -> list[dict[str, Any]]:
    """Discover locally available relative links incorporated by the primary filing."""
    soup = BeautifulSoup(primary_html.read_bytes(), "lxml")
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    for link in soup.find_all("a", href=True):
        label = _normalize(link.get_text(" ", strip=True))
        href = str(link["href"]).strip()
        if not _COMPANION_LABEL.search(label):
            continue
        parsed = urlparse(href)
        local = None if parsed.scheme or parsed.netloc else (primary_html.parent / parsed.path).resolve()
        key = (href, str(local) if local else "")
        exists = bool(local and local.is_file())
        candidates[key] = {
            "label": label[:240],
            "href": href[:400],
            "local_path": str(local) if local else None,
            "exists": exists,
            "provenance": "relative_filing_link" if local else "external_link",
            "sha256": hashlib.sha256(local.read_bytes()).hexdigest() if exists and local else None,
        }
    return sorted(candidates.values(), key=lambda item: (item["href"], item["label"]))


def _page_markers(soup: BeautifulSoup) -> list[tuple[int, int]]:
    positions = _positions(soup)
    markers: list[tuple[int, int]] = []
    for node in soup.find_all(True):
        for raw in (node.get("data-page"), node.get("data-page-number"), node.get("id"), node.get("name")):
            match = re.fullmatch(r"(?:page[_-]?)?(\d+)", str(raw or ""), re.I)
            if match:
                markers.append((int(match.group(1)), positions.get(id(node), -1)))
                break
    for link in soup.find_all("a", href=True):
        match = re.fullmatch(r"(\d{1,3})", _normalize(link.get_text(" ", strip=True)))
        href = str(link["href"])
        if not match or not href.startswith("#") or len(href) == 1:
            continue
        target = soup.find(id=href[1:]) or soup.find(attrs={"name": href[1:]})
        if isinstance(target, Tag):
            markers.append((int(match.group(1)), positions.get(id(target), -1)))
    return sorted(set(markers), key=lambda item: (item[1], item[0]))


def _resolve_interval(soup: BeautifulSoup, page_range: tuple[int, int]) -> tuple[int, int] | None:
    markers = _page_markers(soup)
    starts = [position for page, position in markers if page == page_range[0]]
    if not starts:
        return None
    start = starts[0]
    ends = [position for page, position in markers if page == page_range[1] and position > start]
    return (start, ends[0]) if ends else None


def discover_companion_tables(primary_html: Path, companion_html: Path) -> list[Tag]:
    """Return unique statement tables strictly inside the incorporated page range."""
    page_range = extract_companion_page_range(primary_html)
    if page_range is None:
        return []
    soup = BeautifulSoup(companion_html.read_bytes(), "lxml")
    interval = _resolve_interval(soup, page_range)
    if interval is None:
        return []
    positions = _positions(soup)
    tables: list[Tag] = []
    seen: set[str] = set()
    for table in soup.find_all("table"):
        position = positions.get(id(table), -1)
        if not interval[0] < position < interval[1]:
            continue
        rows = extract_table_rows(table)
        if len({year for row in rows for year in row.values_by_year}) < 2:
            continue
        if not any(_STATEMENT_LABEL.search(row.label) for row in rows):
            continue
        fingerprint = hashlib.sha256(_normalize(table.get_text(" ", strip=True)).encode()).hexdigest()
        if fingerprint not in seen:
            seen.add(fingerprint)
            tables.append(table)
    return tables
