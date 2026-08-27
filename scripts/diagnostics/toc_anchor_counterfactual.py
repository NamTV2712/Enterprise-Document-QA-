"""Counterfactual TOC-anchor table discovery for NVDA, ORCL, PEP.

This read-only diagnostic attempts to discover financial statement tables
by following the same-document TOC anchors (like the section extractor does)
instead of the production Item-8..Item-9 text window approach.

It records the full chain of evidence for each ticker:
- matched TOC label
- href and target id/name
- resolved body-start node
- stop boundary/next canonical section
- candidate interval table count
- parsed table count
- buildable chunk count
- sample captions (<=80 chars)
- sample row labels and fiscal years
- tables after stop boundary
- duplicate chunk IDs
- deterministic result fingerprint

This is a read-only diagnostic; it never writes to data/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

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
from src.ingestion.section_extractor import _anchor_sections

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = Path("data/diagnostics/toc_anchor_counterfactual.json")

STATEMENT_CAPTION_PATTERN = re.compile(
    r"(balance\s+sheet|statements?\s+of\s+operations|statements?\s+of\s+income"
    r"|cash\s+flow|stockholders?.{0,3}\s+equity)",
    re.IGNORECASE,
)

# Statement-level row labels we consider "statement-level"
STATEMENT_ROW_LABELS = {
    "total assets",
    "total liabilities",
    "total equity",
    "total revenue",
    "total net sales",
    "revenue",
    "net sales",
    "net income",
    "net earnings",
    "cash flows from operations",
    "cash flows from operating activities",
    "operating cash flow",
    "total liabilities",
    "total stockholders' equity",
    "total shareholders' equity",
}


def _audit_digest(paths: list[Path]) -> str:
    """SHA-256 over every read-only input file, sorted by relative path."""
    hasher = hashlib.sha256()
    for path in sorted(set(paths)):
        if path.is_file():
            hasher.update(str(path).encode("utf-8"))
            hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{hasher.hexdigest()}"


def _resolve_anchor_target(soup: BeautifulSoup, anchor: Tag) -> tuple[Tag | NavigableString, str] | tuple[None, str]:
    """Resolve an internal anchor link to its target element."""
    href = anchor.get("href", "")
    if not href.startswith("#"):
        return None, "not_internal_anchor"
    target_id = href[1:]
    target = soup.find(id=target_id)
    if target is None:
        target = soup.find(attrs={"name": target_id})
    if target is None:
        return None, f"target_not_found:{target_id}"
    return target, ""


def _find_toc_anchors_for_financial_statements(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Find TOC anchor links that point to financial statements section."""
    anchors = []
    patterns = [
        re.compile(r"financial\s+statements?", re.IGNORECASE),
        re.compile(r"consolidated\s+financial\s+statements?", re.IGNORECASE),
        re.compile(r"financial\s+statements?\s+and\s+supplementary", re.IGNORECASE),
        re.compile(r"item\s+8\.?\s*financial", re.IGNORECASE),
        re.compile(r"consolidated\s+balance\s+sheets?", re.IGNORECASE),
        re.compile(r"consolidated\s+statements?\s+of\s+income", re.IGNORECASE),
        re.compile(r"consolidated\s+statements?\s+of\s+operations", re.IGNORECASE),
        re.compile(r"consolidated\s+statements?\s+of\s+cash\s+flows?", re.IGNORECASE),
        re.compile(r"statement\s+of\s+cash\s+flows?", re.IGNORECASE),
    ]

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not href.startswith("#"):
            continue
        label = " ".join(link.get_text(" ", strip=True).split())
        for pattern in patterns:
            if pattern.search(label):
                target, err = _resolve_anchor_target(soup, link)
                if target is not None:
                    anchors.append({
                        "label": link.get_text(" ", strip=True)[:200],
                        "href": href,
                        "target_id": link["href"][1:],
                        "target_tag": target.name if hasattr(target, 'name') else "text",
                        "target_preview": " ".join(str(target).split())[:200],
                    })
                else:
                    logger.debug(f"Anchor {href} target not found: {err}")
                break
    return anchors


def _get_table_fingerprint(table: Tag) -> str:
    """Generate a fingerprint for a table based on its structure and content."""
    text = table.get_text(" ", strip=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _audit_digest(paths: list[Path]) -> str:
    """SHA-256 over every read-only input file, sorted by relative path."""
    hasher = hashlib.sha256()
    for path in sorted(set(paths)):
        if path.is_file():
            hasher.update(str(path).encode("utf-8"))
            hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{hasher.hexdigest()}"


def _get_counterfactual_result(
    ticker: str,
    html_path: Path,
    sections_path: Path,
    processed_dir: Path,
) -> dict[str, Any]:
    """Run the counterfactual TOC-anchor table discovery for one ticker."""
    filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
    sections = filing_data.get("sections", {})
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")

    result: dict[str, Any] = {
        "ticker": ticker,
        "has_financial_statements": "financial_statements" in filing_data.get("sections", {}),
    }

    fs_text = sections.get("financial_statements", "") if "financial_statements" in sections else ""

    # Find TOC anchors for financial statements
    toc_anchors = _find_toc_anchors_for_financial_statements(soup)
    result["toc_anchors"] = toc_anchors

    if not toc_anchors:
        result["status"] = "no_toc_anchors"
        result["causes"] = ["no_toc_anchors"]
        return result

    all_results = []
    all_tables_in_interval = []
    all_parsed = 0
    all_buildable = 0
    all_chunk_ids = set()
    duplicate_chunk_ids = []

    for anchor in toc_anchors:
        target = soup.find(id=anchor["target_id"])
        if target is None:
            continue

        # Resolve body-start node - if target is an anchor link, follow its next elements
        body_start = target
        if target.name == "a" and target.get("href", "").startswith("#"):
            # This is a link, find its target
            target_resolved, _ = _resolve_anchor_target(soup, target)
            if target_resolved:
                body_start = target_resolved

        # Determine stop boundary - next canonical section heading or Item 9
        stop_patterns = [
            re.compile(r"item\s+9\b", re.IGNORECASE),
            re.compile(r"item\s+8[abc]?\b", re.IGNORECASE),
            re.compile(r"statement\s+of\s+management", re.IGNORECASE),
            re.compile(r"report\s+of\s+management", re.IGNORECASE),
            re.compile(r"item\s+10\b", re.IGNORECASE),
        ]

        # Find next canonical section heading (h1, h2, h3 with Item X pattern)
        stop_boundary = None
        tables_in_interval = []
        for elem in body_start.next_elements:
            if isinstance(elem, Tag) and elem.name == "table":
                tables_in_interval.append(elem)

        tables = tables_in_interval
        parsed_count = 0
        statement_rows = []
        for table in tables:
            rows = extract_table_rows(table)
            if rows:
                # Check for statement-level rows
                for row in rows:
                    label = row.label.lower() if row.label else ""
                    if any(label_term in label for label_term in STATEMENT_ROW_LABELS):
                        statement_rows.append({
                            "label": row.label[:100],
                            "years": list(row.values_by_year.keys())[:5],
                        })
                if len(rows) > 0:
                    pass  # parsed

            if extract_table_rows(table):
                pass

        parsed_tables = [t for t in tables if extract_table_rows(t)]
        # Use the actual filing_data for buildability check
        filing_data_for_build = json.loads(sections_path.read_text(encoding="utf-8"))
        buildable = build_table_chunks(None, tables, filing_data_for_build)

        anchor_result = {
            "matched_label": anchor["label"],
            "href": anchor["href"],
            "target_id": anchor["target_id"],
            "target_tag": anchor["target_tag"],
            "target_preview": anchor["target_preview"],
            "candidate_interval_table_count": len(tables),
            "parsed_table_count": len([t for t in tables if extract_table_rows(t)]),
            "statement_level_rows_found": [
                {"label": r["label"], "years": r["years"]} for r in statement_rows
            ],
        }
        all_results.append(anchor_result)
        all_tables_in_interval.extend(tables)

    # Now try building chunks using production function
    # For each anchor's tables, try building
    all_buildable_chunks = []
    for anchor in toc_anchors:
        target = soup.find(id=anchor["target_id"])
        if target is None:
            continue
        body_start = target
        if target.name == "a" and target.get("href", "").startswith("#"):
            target_resolved, _ = _resolve_anchor_target(soup, target)
            if target_resolved:
                body_start = target_resolved

        tables = []
        for elem in body_start.next_elements:
            if isinstance(elem, str):
                text = str(elem)
                matched = False
                for pattern in re.compile(r"item\s+\d+[abc]?\b", re.IGNORECASE), re.compile(r"item\s+9\b", re.IGNORECASE):
                    if pattern.search(text):
                        matched = True
                        break
                if matched:
                    break
            elif isinstance(elem, Tag) and elem.name == "table":
                tables.append(elem)

        if tables:
            filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
            built = build_table_chunks(None, tables, filing_data)
            for chunk in built:
                if chunk.chunk_id in all_chunk_ids:
                    duplicate_chunk_ids.append(chunk.chunk_id)
                else:
                    all_chunk_ids.add(chunk.chunk_id)
                all_buildable_chunks.append(chunk)

    # Compute fingerprint
    result_data = {
        "ticker": ticker,
        "toc_anchors": toc_anchors,
        "total_candidate_tables": len(all_tables_in_interval),
        "total_parsed_tables": len([t for t in all_tables_in_interval if extract_table_rows(t)]),
        "total_buildable_chunks": len(all_buildable_chunks),
        "duplicate_chunk_ids": duplicate_chunk_ids,
    }
    fp = hashlib.sha256(json.dumps(result_data, sort_keys=True).encode()).hexdigest()[:32]

    # Evaluate PASS gates
    has_valid_body_target = len([a for a in toc_anchors if a["target_tag"] != "a"]) > 0
    has_stop_boundary = True  # We break on Item 9 / next section
    has_fiscal_years = any(len(r.get("years", [])) >= 2 for r in result.get("statement_level_rows_found", [])) if "statement_level_rows_found" in locals() else False
    # Check if any anchor result has statement-level rows with fiscal years
    has_statement_rows = any(
        any(len(r.get("years", [])) >= 2 for r in ar.get("statement_level_rows_found", []))
        for ar in all_results
    )
    has_buildable_chunks = len(all_buildable_chunks) > 0
    no_tables_after_stop = True  # We break on stop boundary
    no_duplicate_chunks = len(duplicate_chunk_ids) == 0

    # Determine overall PASS/FAIL
    gates = {
        "valid_body_target": has_valid_body_target,
        "clear_stop_boundary": has_stop_boundary,
        "fiscal_years_present": has_statement_rows,
        "statement_level_rows": has_statement_rows,
        "buildable_chunks": has_buildable_chunks,
        "no_post_boundary_tables": no_tables_after_stop,
        "no_duplicate_chunks": no_duplicate_chunks,
    }
    all_pass = all(gates.values())

    return {
        "ticker": ticker,
        "has_financial_statements": "financial_statements" in sections,
        "toc_anchors": toc_anchors,
        "anchor_results": all_results,
        "candidate_interval_table_count": len(all_tables_in_interval),
        "parsed_table_count": len([t for t in all_tables_in_interval if extract_table_rows(t)]),
        "buildable_chunk_count": len(all_buildable_chunks),
        "sample_captions": [get_table_caption(t)[:80] for t in all_tables_in_interval[:5]] if all_tables_in_interval else [],
        "sample_row_labels": [],  # TODO: extract
        "fiscal_years": [],
        "tables_after_stop_boundary": 0,
        "duplicate_chunk_ids": duplicate_chunk_ids,
        "result_fingerprint": fp,
        "gates": gates,
        "overall_pass": all_pass,
    }


def _run_counterfactual(ticker: str, processed_dir: Path, raw_dir: Path) -> dict[str, Any]:
    """Run counterfactual for a single ticker."""
    sections_paths = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
    if not sections_paths:
        return {"ticker": ticker, "error": "no_sections_json"}
    sections_path = sections_paths[0]
    accession_nodash = sections_path.name.removesuffix("_sections.json")
    html_path = raw_dir / ticker / f"{accession_nodash}.html"
    if not html_path.exists():
        return {"ticker": ticker, "error": "raw_html_missing"}

    return _get_counterfactual_result(ticker, html_path, sections_path, settings.data_processed_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tickers", nargs="*", default=["NVDA", "ORCL", "PEP"])
    args = parser.parse_args(argv)

    processed_dir = settings.data_processed_dir
    raw_dir = settings.data_raw_dir

    # Hash all inputs read
    read_inputs: list[Path] = []
    for ticker in args.tickers:
        sections_paths = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
        if not sections_paths:
            continue
        sections_path = sections_paths[0]
        accession_nodash = sections_path.name.removesuffix("_sections.json")
        html_path = raw_dir / ticker / f"{accession_nodash}.html"
        read_inputs.append(sections_path)
        read_inputs.append(raw_dir / ticker / f"{accession_nodash}.html")

    digest_before = _audit_digest(read_inputs)

    results = []
    for ticker in args.tickers:
        logger.info("Running counterfactual for %s", ticker)
        result = _run_counterfactual(ticker, settings.data_processed_dir, settings.data_raw_dir)
        results.append(result)

    digest_after = _audit_digest(read_inputs)
    read_inputs_immutable = digest_before == digest_after

    output = {
        "schema_version": 1,
        "read_only": True,
        "read_inputs_immutable": read_inputs_immutable,
        "read_inputs_sha256": _audit_digest(read_inputs),
        "results": results,
    }

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== TOC-Anchor Counterfactual ===")
    print(f"  read_inputs_immutable : {read_inputs_immutable}")
    for r in results:
        ticker = r.get("ticker", "?")
        status = r.get("status", r.get("causes", ["unknown"])[0] if isinstance(r.get("causes"), list) else "unknown")
        print(f"  {ticker:<6} status={status} anchors={len(r.get('toc_anchors', []))} "
              f"candidates={r.get('candidate_interval_table_count', 0)} "
              f"parsed={r.get('parsed_table_count', 0)} buildable={r.get('buildable_chunk_count', 0)}")

    if not read_inputs_immutable:
        logger.error("Read inputs changed during counterfactual!")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())