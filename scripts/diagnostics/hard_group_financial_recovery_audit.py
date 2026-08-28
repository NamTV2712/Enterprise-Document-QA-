"""Read-only route audit for CVX, XOM, JPM, and IBM financial statements."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from configs.settings import settings
from src.ingestion.section_extractor import extract_sections_from_html
from src.ingestion.table_extractor import extract_table_rows, get_table_caption

DEFAULT_OUTPUT = Path("data/diagnostics/hard_group_financial_recovery_audit.json")
DEFAULT_TICKERS = ("CVX", "XOM", "JPM", "IBM")
SCHEMA_VERSION = 1
_ITEM8 = re.compile(r"^item\s+8\b", re.IGNORECASE)
_FINANCIAL_LINK = re.compile(
    r"financial table of contents|financial statements|consolidated|balance sheets?"
    r"|cash flows?|stockholders?.{0,4}equity",
    re.IGNORECASE,
)
_EXTERNAL_ANNUAL_REPORT = re.compile(
    r"annual report to stockholders.{0,220}(?:incorporated|reference)",
    re.IGNORECASE | re.DOTALL,
)
_CONTAMINATION = re.compile(r"\b(?:item\s+9|part\s+iv|signatures?)\b", re.IGNORECASE)
_STATEMENT_ROW = re.compile(
    r"net (?:income|earnings|revenue)|total (?:assets|liabilities|revenues?)"
    r"|cash flows?|stockholders?.{0,4}equity|shareholders?.{0,4}equity",
    re.IGNORECASE,
)


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_inputs(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: str(item)):
        if path.is_file():
            digest.update(str(path).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{digest.hexdigest()}"


def _find_paths(ticker: str, processed_dir: Path, raw_dir: Path) -> tuple[Path, Path, Path]:
    matches = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one sections file for {ticker}, found {len(matches)}")
    sections_path = matches[0]
    accession = sections_path.stem.removesuffix("_sections")
    html_path = raw_dir / ticker / f"{accession}.html"
    chunks_path = sections_path.with_name(f"{accession}_chunks.jsonl")
    if not html_path.is_file() or not chunks_path.is_file():
        raise FileNotFoundError(f"missing raw HTML or chunks for {ticker}")
    return html_path, sections_path, chunks_path


def _positions(soup: BeautifulSoup) -> dict[int, int]:
    return {id(node): index for index, node in enumerate(soup.descendants)}


def _root_item8_nodes(soup: BeautifulSoup, positions: dict[int, int]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    for node in soup.find_all(string=True):
        text = " ".join(str(node).split())
        if not _ITEM8.match(text):
            continue
        parent = node.parent if isinstance(node.parent, Tag) else None
        if parent is None:
            continue
        roots.append({
            "position": positions.get(id(parent)),
            "tag": parent.name,
            "text": text[:240],
        })
    return roots[:12]


def _financial_link_targets(soup: BeautifulSoup, positions: dict[int, int]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None]] = set()
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        href = str(link["href"])
        if not _FINANCIAL_LINK.search(label):
            continue
        target = None
        if href.startswith("#") and len(href) > 1:
            target = soup.find(id=href[1:]) or soup.find(attrs={"name": href[1:]})
        target_position = positions.get(id(target)) if isinstance(target, Tag) else None
        key = (label, target_position)
        if key in seen:
            continue
        seen.add(key)
        targets.append({
            "label": label[:240],
            "href": href[:240],
            "target_position": target_position,
            "target_preview": " ".join(target.get_text(" ", strip=True).split())[:240] if isinstance(target, Tag) else "",
        })
    return sorted(targets, key=lambda item: (item["target_position"] is None, item["target_position"] or 0, item["label"]))


def _statement_table_evidence(soup: BeautifulSoup, positions: dict[int, int]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for index, table in enumerate(soup.find_all("table")):
        rows = extract_table_rows(table)
        labels = [row.label for row in rows]
        if not labels or not _STATEMENT_ROW.search(" | ".join(labels)):
            continue
        evidence.append({
            "table_index": index,
            "position": positions.get(id(table)),
            "caption": " ".join(get_table_caption(table).split())[:180],
            "row_labels": labels[:12],
            "fiscal_years": sorted({year for row in rows for year in row.values_by_year}),
        })
    return evidence


def _fresh_quality(stored: dict[str, str], fresh: dict[str, str]) -> dict[str, Any]:
    financial = fresh.get("financial_statements", "")
    mdna = fresh.get("mdna", "")
    fs_in_mdna = bool(financial and financial in mdna)
    mdna_in_fs = bool(mdna and mdna in financial)
    contamination = sorted({match.group(0).lower() for match in _CONTAMINATION.finditer(financial)})
    return {
        "stored_financial_statements_chars": len(stored.get("financial_statements", "")),
        "fresh_financial_statements_chars": len(financial),
        "fresh_mdna_chars": len(mdna),
        "fresh_fs_is_substring_of_mdna": fs_in_mdna,
        "fresh_mdna_is_substring_of_fs": mdna_in_fs,
        "fresh_fs_contamination_markers": contamination,
        "fresh_fs_quality_valid": bool(financial) and not fs_in_mdna and not contamination,
    }


def _classify_route(
    ticker: str,
    html_text: str,
    roots: list[dict[str, Any]],
    link_targets: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> str:
    if _EXTERNAL_ANNUAL_REPORT.search(html_text) and len(tables) < 40:
        return "external_annual_report_required"
    if any("financial table of contents" in target["label"].casefold() for target in link_targets):
        return "same_document_internal_index"
    if roots and link_targets and tables:
        return "same_document_page_anchor"
    return "insufficient_evidence"


def audit_filing(html_path: Path, sections_path: Path, chunks_path: Path) -> dict[str, Any]:
    filing = json.loads(sections_path.read_text(encoding="utf-8"))
    html = html_path.read_bytes()
    soup = BeautifulSoup(html, "lxml")
    positions = _positions(soup)
    fresh = extract_sections_from_html(html)
    stored_sections = filing.get("sections", {})
    roots = _root_item8_nodes(soup, positions)
    links = _financial_link_targets(soup, positions)
    tables = _statement_table_evidence(soup, positions)
    quality = _fresh_quality(stored_sections, fresh.sections)
    route = _classify_route(filing["ticker"], soup.get_text(" ", strip=True), roots, links, tables)
    route_supported = route.startswith("same_document") and bool(roots and links and tables)
    return {
        "schema_version": SCHEMA_VERSION,
        "ticker": filing["ticker"],
        "route_classification": route,
        "route_supported_by_current_raw_document": route_supported,
        "root_item8_nodes": roots,
        "financial_link_targets": links,
        "statement_table_evidence": tables,
        "statement_table_count": len(tables),
        "fresh_extraction": quality,
        "stored_section_names": sorted(stored_sections),
        "fresh_section_names": sorted(fresh.sections),
        "fresh_warnings": fresh.warnings,
        "production_ready": False,
        "next_action": (
            "design a generic same-document resolver from audited internal targets"
            if route_supported
            else "obtain and validate the referenced annual-report document before extraction work"
            if route == "external_annual_report_required"
            else "collect more structural evidence before changing extraction"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tickers", nargs="*", default=list(DEFAULT_TICKERS))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    paths = [_find_paths(ticker, settings.data_processed_dir, settings.data_raw_dir) for ticker in args.tickers]
    inputs = [path for triplet in paths for path in triplet]
    before = _digest_inputs(inputs)
    results = [audit_filing(*triplet) for triplet in paths]
    after = _digest_inputs(inputs)
    report = {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "read_inputs_immutable": before == after,
        "read_inputs_sha256": after,
        "results": results,
    }
    report["report_fingerprint"] = _sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result['ticker']}: {result['route_classification']} tables={result['statement_table_count']}")
    return 0 if report["read_inputs_immutable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
