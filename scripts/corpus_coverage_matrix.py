"""Read-only corpus coverage audit across configured tickers.

Builds a deterministic ticker x section x financial_table coverage matrix
from the embedded chunk artifacts that the retriever actually serves.
The audit never writes into the corpus directory: it only opens chunk
files for reading, so repeated runs must produce byte-identical output.

Usage (from the project root):
    python -m scripts.corpus_coverage_matrix [--data-dir PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from configs.settings import settings
from configs.tickers import TICKERS
from src.retrieval.index_manifest import compute_corpus_fingerprint

SCHEMA_VERSION = 1
TEXT_SECTIONS = ("business", "risk_factors", "mdna", "financial_statements")
TABLE_SECTION = "financial_table"


def _load_ticker_chunks(ticker_dir: Path) -> list[tuple[str, dict]]:
    """Return (file_name, record) pairs for one ticker's embedded chunks."""
    pairs: list[tuple[str, dict]] = []
    for path in sorted(ticker_dir.glob("*_chunks_embedded.jsonl")):
        with path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                pairs.append((path.name, json.loads(line)))
    return pairs


def audit_ticker(ticker_dir: Path, ticker: str) -> dict[str, Any]:
    """Summarize section and financial-table coverage for one ticker."""
    file_records = _load_ticker_chunks(ticker_dir)
    sections_present: set[str] = set()
    has_table = False
    text_chunk_count = 0
    table_chunk_count = 0
    source_files: set[str] = set()

    for file_name, record in file_records:
        section = record.get("section")
        if section == TABLE_SECTION:
            table_chunk_count += 1
            has_table = True
        elif section in TEXT_SECTIONS:
            text_chunk_count += 1
            sections_present.add(section)
        source_files.add(file_name)

    sections_missing = [s for s in TEXT_SECTIONS if s not in sections_present]
    if not file_records:
        status = "missing"
    elif sections_missing:
        status = "degraded"
    else:
        status = "clean"

    return {
        "ticker": ticker,
        "status": status,
        "sections_present": sorted(sections_present),
        "sections_missing": sections_missing,
        "has_financial_table": has_table,
        "text_chunk_count": text_chunk_count,
        "financial_table_chunk_count": table_chunk_count,
        "total_chunk_count": text_chunk_count + table_chunk_count,
        "embedded_file_count": len(source_files),
    }


def build_coverage_report(
    data_processed_dir: Path,
    tickers: list[str] | None = None,
) -> dict[str, Any]:
    """Build the full deterministic coverage report for the corpus."""
    configured = list(tickers) if tickers is not None else list(TICKERS)
    rows = [
        audit_ticker(data_processed_dir / ticker, ticker)
        for ticker in sorted(configured)
    ]

    searchable = [row for row in rows if row["status"] != "missing"]
    all_chunks = []
    for path in sorted(data_processed_dir.glob("*/*_chunks_embedded.jsonl")):
        with path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                all_chunks.append(json.loads(line))

    return {
        "schema_version": SCHEMA_VERSION,
        "corpus_fingerprint": compute_corpus_fingerprint(all_chunks)
        if all_chunks
        else None,
        "summary": {
            "configured_tickers": len(configured),
            "searchable_tickers": len(searchable),
            "clean_tickers": sum(1 for r in rows if r["status"] == "clean"),
            "degraded_tickers": sum(1 for r in rows if r["status"] == "degraded"),
            "missing_tickers": sum(1 for r in rows if r["status"] == "missing"),
            "tickers_with_financial_table": sum(
                1 for r in rows if r["has_financial_table"]
            ),
            "total_chunks": sum(r["total_chunk_count"] for r in rows),
        },
        "tickers": rows,
    }


def render_terminal_report(report: dict[str, Any]) -> str:
    """Render a concise human-readable summary of the coverage matrix."""
    summary = report["summary"]
    lines = [
        "Corpus coverage matrix",
        f"  Schema version:              {report['schema_version']}",
        f"  Corpus fingerprint:          {report['corpus_fingerprint']}",
        f"  Configured tickers:          {summary['configured_tickers']}",
        f"  Searchable tickers:          {summary['searchable_tickers']}",
        f"  Clean tickers:               {summary['clean_tickers']}",
        f"  Degraded tickers:            {summary['degraded_tickers']}",
        f"  Missing tickers:             {summary['missing_tickers']}",
        f"  With financial_table:        {summary['tickers_with_financial_table']}",
        f"  Total chunks:                {summary['total_chunks']}",
    ]

    degraded = [r["ticker"] for r in report["tickers"] if r["status"] == "degraded"]
    missing_sections_note = [
        f"{r['ticker']} (missing: {', '.join(r['sections_missing'])})"
        for r in report["tickers"]
        if r["status"] == "degraded"
    ]
    no_table = [
        r["ticker"] for r in report["tickers"]
        if r["status"] != "missing" and not r["has_financial_table"]
    ]
    missing = [r["ticker"] for r in report["tickers"] if r["status"] == "missing"]

    lines.append("")
    lines.append("Degraded tickers:")
    if missing_sections_note:
        lines.extend(f"  - {note}" for note in missing_sections_note)
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Searchable tickers without financial_table chunks:")
    if no_table:
        lines.append(f"  {', '.join(no_table)}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Missing tickers (no embedded chunks):")
    if missing:
        lines.append(f"  {', '.join(missing)}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def report_to_json(report: dict[str, Any]) -> str:
    """Serialize the report deterministically for diffing and storage."""
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=settings.data_processed_dir,
        help="Processed corpus directory (default from settings)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON report",
    )
    args = parser.parse_args(argv)

    report = build_coverage_report(args.data_dir)
    print(render_terminal_report(report))
    if args.output is not None:
        args.output.write_text(report_to_json(report), encoding="utf-8")
        print(f"\nJSON report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
