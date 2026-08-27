"""Read-only financial-table coverage audit for tickers without table chunks.

For every configured ticker whose served corpus lacks ``financial_table``
chunks this diagnostic walks the exact production funnel and records where
the tables are lost:

1. ``source_missing``            raw filing HTML absent
2. ``financial_statements_missing`` extracted sections lack Item 8 text
3. ``parser_miss``               the FS start anchor cannot be located in DOM
4. ``html_table_missing``        anchor found but zero <table> before Item 9,
                                 and no statement-caption table exists anywhere
5. ``layout_or_exhibit``         statements exist as tables elsewhere in the
                                 document (exhibit/part split) outside the window
6. ``row_filter_miss``           window tables exist but none yield year-header
                                 rows under ``extract_table_rows``
7. ``pipeline_stale``            chunks WOULD be built now but the embedded
                                 artifacts contain no financial_table records

The script never writes under ``data/``; it creates an ignored report artifact
under ``data/diagnostics/`` but does not modify raw/processed corpus inputs.

Usage:
    python -m scripts.diagnostics.financial_table_audit [--output PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from configs.settings import settings
from scripts.diagnostics.diagnose_all_financial_tables import (
    _candidate_start_snippets,
    find_tables_in_financial_section,
)
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_extractor import (
    extract_table_rows,
    get_table_caption,
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = Path("data/diagnostics/financial_table_audit.json")

STATEMENT_CAPTION_PATTERN = re.compile(
    r"(balance\s+sheet|statements?\s+of\s+operations|statements?\s+of\s+income"
    r"|cash\s+flow|stockholders?.{0,3}\s+equity)",
    re.IGNORECASE,
)


def _audit_digest(paths: list[Path]) -> str:
    """SHA-256 over every read-only input file, sorted by relative path."""
    hasher = hashlib.sha256()
    for path in sorted(set(paths)):
        if path.is_file():
            hasher.update(str(path).encode("utf-8"))
            hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{hasher.hexdigest()}"


def _embedded_table_count(ticker_dir: Path) -> int | None:
    counts = [
        sum(
            1 for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
            and json.loads(line).get("section") == "financial_table"
        )
        for path in ticker_dir.glob("*_chunks_embedded.jsonl")
    ]
    return sum(counts) if counts else None


def _doc_statement_caption_samples(soup: BeautifulSoup, limit: int = 5) -> list[str]:
    """Short captions of statement-like tables anywhere in the document."""
    samples: list[str] = []
    for table in soup.find_all("table"):
        if len(samples) >= limit:
            break
        caption = get_table_caption(table)
        if caption and STATEMENT_CAPTION_PATTERN.search(caption):
            sample = " ".join(caption.split())[:80]
            if sample not in samples:
                samples.append(sample)
    return samples


STATEMENT_CAPTION_PATTERN = re.compile(
    r"(balance\s+sheet|statements?\s+of\s+operations|statements?\s+of\s+income"
    r"|cash\s+flow|stockholders?.{0,3}\s+equity)",
    re.IGNORECASE,
)


def _audit_one(
    ticker: str,
    html_path: Path,
    sections_path: Path,
    processed_dir: Path,
) -> dict[str, Any]:
    report: dict[str, Any] = {"ticker": ticker}

    filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
    sections = filing_data.get("sections", {})
    report["has_financial_statements"] = "financial_statements" in sections
    report["fs_text_chars"] = len(sections.get("financial_statements", ""))
    report["embedded_financial_table_chunks"] = _embedded_table_count(
        processed_dir / ticker
    )

    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    report["total_html_tables"] = len(soup.find_all("table"))

    # Statement-like tables anywhere in the document
    statement_like_anywhere = _doc_statement_caption_samples(soup)
    report["statement_like_tables_anywhere"] = statement_like_anywhere

    if "financial_statements" not in sections:
        report["has_financial_statements"] = False
        report["fs_text_chars"] = 0
        report["window_table_count"] = 0
        report["statement_like_tables_outside_window"] = []
        report["tables_with_parsed_rows"] = 0
        report["chunks_buildable_now"] = 0
        report["causes"] = ["financial_statements_missing"]
        report["evidence"] = {
            "total_html_tables": report["total_html_tables"],
            "statement_like_tables_anywhere": statement_like_anywhere,
        }
        report["confidence"] = "high"
        report["remediation"] = (
            "Extend extraction recovery (incorporation-by-reference / "
            "annual-report TOC layouts) before table work can apply."
        )
        return report

    report["has_financial_statements"] = True
    fs_text = sections.get("financial_statements", "")
    report["fs_text_chars"] = len(fs_text)

    # Stage 1: production window discovery.
    tables = find_tables_in_financial_section(html_path, sections_path)
    report["window_table_count"] = len(tables)

    causes: list[str] = []
    if not tables:
        start_node_found = any(
            soup.find(string=lambda text: text and snippet in text)
            is not None
            for snippet in _candidate_start_snippets(
                sections["financial_statements"]
            )
        )
        report["start_anchor_found"] = bool(start_node_found)
        report["statement_like_tables_outside_window"] = statement_like_anywhere
        report["window_table_count"] = 0
        report["tables_with_parsed_rows"] = 0
        report["chunks_buildable_now"] = 0

        if start_node_found:
            # Anchor found but no tables in window - check if statement tables exist elsewhere
            if statement_like_anywhere:
                causes.append("layout_or_exhibit")
                report["remediation"] = (
                    "Statements live outside the Item-8..Item-9 DOM window "
                    "(separate part/exhibit); extend the table-discovery "
                    "window or follow exhibit references."
                )
            else:
                # Anchor found but no tables anywhere
                causes.append("html_table_missing")
                report["remediation"] = (
                    "Valid FS anchor but no <table> elements in window "
                    "and no statement-like tables anywhere in document."
                )
        else:
            causes.append("parser_miss")
            report["remediation"] = (
                "FS start anchor text does not match any DOM node; align "
                "anchor snippets with the recovered section text."
            )
        report["causes"] = causes
        report["confidence"] = "high" if start_node_found else "medium"
        report["tables_with_parsed_rows"] = 0
        report["chunks_buildable_now"] = 0
        report["statement_like_tables_outside_window"] = statement_like_anywhere
        return report

    # Stage 2: year-header row parsing.
    parsed_rows: list[int] = []
    captions: list[str] = []
    for table in tables:
        rows = extract_table_rows(table)
        parsed_rows.append(len(rows))
        if rows:
            caption = get_table_caption(table)
            if caption:
                captions.append(" ".join(caption.split())[:80])

    tables_with_parsed = sum(1 for n in parsed_rows if n > 0)
    report["tables_with_parsed_rows"] = tables_with_parsed
    report["sample_captions"] = captions[:5]

    if not any(parsed_rows):
        causes.append("row_filter_miss")
        report["remediation"] = (
            "Tables exist but extract_table_rows finds no year-header row; "
            "extend header detection (e.g., 'Dec. 31,' styles or fiscal labels)."
        )
        report["confidence"] = "high"

    # Statement-like tables outside the window
    tables_in_window = {id(t) for t in tables}
    outside_captions: list[str] = []
    for table in soup.find_all("table"):
        if id(table) in tables_in_window:
            continue
        caption = get_table_caption(table)
        if caption and STATEMENT_CAPTION_PATTERN.search(caption):
            sample = " ".join(caption.split())[:80]
            if sample not in outside_captions:
                outside_captions.append(sample)
    report["statement_like_tables_outside_window"] = outside_captions[:5]

    # Stage 3: what would production build right now vs what is served.
    built = build_table_chunks(html_path, tables, filing_data)
    report["chunks_buildable_now"] = len(built)
    embedded = report.get("embedded_financial_table_chunks") or 0

    if built and embedded == 0:
        causes.append("pipeline_stale")
        report["remediation"] = (
            "Rebuildable today; rerun add_table_chunks -> embed_chunks -> "
            "index_chunks for this generation."
        )
    elif not any(parsed_rows) and "row_filter_miss" not in causes:
        causes.append("row_filter_miss")
        report["remediation"] = (
            "All window tables failed year-header parsing; see row_filter_miss."
        )
    elif not causes:
        causes.append("none")
        report["remediation"] = "No defect detected at any funnel stage."

    report["causes"] = causes
    report["tables_with_parsed_rows"] = tables_with_parsed
    report["chunks_buildable_now"] = len(built)
    report["statement_like_tables_outside_window"] = outside_captions[:5]

    return report


def _audit_digest(paths: list[Path]) -> str:
    """SHA-256 over every read-only input file, sorted by relative path."""
    hasher = hashlib.sha256()
    for path in sorted(set(paths)):
        if path.is_file():
            hasher.update(str(path).encode("utf-8"))
            hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{hasher.hexdigest()}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    processed_dir: Path = settings.data_processed_dir
    raw_dir: Path = settings.data_raw_dir
    configured = [
        path.name for path in sorted(processed_dir.iterdir()) if path.is_dir()
    ]

    # Collect the exact read-only inputs first so the immutability proof
    # hashes only what the audit reads (fast and deterministic).
    read_inputs: list[Path] = []
    targets: list[tuple[str, Path, Path, int]] = []
    for ticker in configured:
        embedded_count = _embedded_table_count(processed_dir / ticker)
        if embedded_count is None or embedded_count > 0:
            continue
        sections_paths = sorted(
            processed_dir.glob(f"{ticker}/*_sections.json")
        )
        if not sections_paths:
            continue
        sections_path = sections_paths[0]
        accession_nodash = sections_path.name.removesuffix("_sections.json")
        html_path = raw_dir / ticker / f"{accession_nodash}.html"
        embedded_files = list((processed_dir / ticker).glob("*_chunks_embedded.jsonl"))
        read_inputs.extend([sections_path, html_path, *embedded_files])
        targets.append((ticker, html_path, sections_path, 0))  # embedded_count will be set per entry

    digest_before = _audit_digest(read_inputs)
    audited: list[dict[str, Any]] = []
    for ticker, html_path, sections_path, _ in targets:
        logger.info("Auditing %s", ticker)
        entry = _audit_one(ticker, html_path, sections_path, settings.data_processed_dir)
        entry["embedded_financial_table_chunks"] = _embedded_table_count(
            settings.data_processed_dir / ticker
        )
        audited.append(entry)

    digest_after = _audit_digest(read_inputs)
    read_inputs_immutable = digest_before == digest_after

    output = {
        "schema_version": 2,
        "read_only": True,
        "read_inputs_immutable": read_inputs_immutable,
        "read_inputs_sha256": _audit_digest(read_inputs),
        "tickers_audited": [entry["ticker"] for entry in audited],
        "results": audited,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== Financial-table audit v2 ===")
    print(f"  read_inputs_immutable : {read_inputs_immutable}")
    for entry in audited:
        print(
            f"  {entry['ticker']:<6} causes={entry['causes']} "
            f"buildable_now={entry.get('chunks_buildable_now')} "
            f"window_tables={entry.get('window_table_count')}"
            f" statement_like_outside={len(entry.get('statement_like_tables_outside_window', []))}"
        )
    if not read_inputs_immutable:
        logger.error("Read inputs changed during audit!")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())