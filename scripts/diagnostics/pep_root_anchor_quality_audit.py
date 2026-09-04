"""Read-only quality audit for PEP's root-anchor financial-table fallback."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bs4 import Tag

from configs.settings import settings
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_discovery import discover_root_anchor_tables
from src.ingestion.table_extractor import extract_table_rows, get_table_caption

DEFAULT_OUTPUT = Path("data/diagnostics/pep_root_anchor_quality_audit.json")
SCHEMA_VERSION = 1


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_inputs(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: str(item)):
        if path.is_file():
            digest.update(str(path).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{digest.hexdigest()}"


def _table_fingerprint(table: Tag) -> str:
    text = " ".join(table.get_text(" ", strip=True).split())
    return _sha256_bytes(text.encode())


def _classify_table(labels: list[str]) -> tuple[str, str]:
    """Classify only from parsed table rows, with the matching evidence recorded."""
    lowered = [label.lower() for label in labels]
    joined = " | ".join(lowered)
    if all(marker in joined for marker in ("net revenue", "cost of sales", "gross profit")):
        return "primary_income_statement", "net revenue + cost of sales + gross profit"
    if "net currency translation adjustment" in joined:
        return "primary_comprehensive_income", "net currency translation adjustment"
    if "operating activities - net income" in joined and "depreciation" in joined:
        return "primary_cash_flow_statement", "operating activities net income + depreciation"
    if "current assets - cash and cash equivalents" in joined and "inventories" in joined:
        return "primary_balance_sheet", "current assets cash + inventories"
    if "common stock - balance, beginning of year" in joined and "common stock - balance, end of year" in joined:
        return "primary_equity_statement", "common stock opening + closing balance"
    if any(marker in joined for marker in ("pension", "retiree medical", "tax", "lease", "share-based")):
        return "financial_note", "pension/tax/lease/share-based row marker"
    if any(marker in joined for marker in ("cash flow", "net income", "assets", "liabilit", "revenue", "income")):
        return "supporting_financial_table", "financial row marker without primary-statement signature"
    return "other_financial_table", "no primary-statement or note signature"


def _find_paths(ticker: str, processed_dir: Path, raw_dir: Path) -> tuple[Path, Path, Path]:
    sections_paths = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
    if len(sections_paths) != 1:
        raise FileNotFoundError(f"expected one sections file for {ticker}, found {len(sections_paths)}")
    sections_path = sections_paths[0]
    accession = sections_path.stem.removesuffix("_sections")
    html_path = raw_dir / ticker / f"{accession}.html"
    chunks_path = sections_path.with_name(f"{accession}_chunks.jsonl")
    if not html_path.is_file() or not chunks_path.is_file():
        raise FileNotFoundError(f"missing raw HTML or chunks for {ticker}")
    return html_path, sections_path, chunks_path


def _canonical_table_records(chunks_path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("section") == "financial_table":
            records.append({"chunk_id": record["chunk_id"], "text": record["text"]})
    return records


def _without_unit_line(text: str) -> str:
    """Compare legacy canonical chunks without pending unit metadata."""
    return "\n".join(
        line for line in text.splitlines() if not line.startswith("Units:")
    )


def _core_table_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {**record, "text": _without_unit_line(record["text"])}
        for record in records
    ]


def audit_pep_root_anchor_tables(
    html_path: Path,
    sections_path: Path,
    chunks_path: Path,
) -> dict[str, Any]:
    """Return deterministic quality evidence without changing any input artifact."""
    filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
    tables = discover_root_anchor_tables(html_path)
    candidate_chunks = build_table_chunks(html_path, tables, filing_data)
    canonical_records = _canonical_table_records(chunks_path)
    classifications: list[dict[str, Any]] = []
    for index, table in enumerate(tables):
        rows = extract_table_rows(table)
        labels = [row.label for row in rows]
        years = sorted({year for row in rows for year in row.values_by_year})
        classification, reason = _classify_table(labels)
        classifications.append({
            "table_index": index,
            "table_fingerprint": _table_fingerprint(table),
            "caption": " ".join(get_table_caption(table).split())[:200],
            "classification": classification,
            "classification_reason": reason,
            "row_count": len(rows),
            "row_labels": labels,
            "fiscal_years": years,
            "candidate_chunk_id": candidate_chunks[index].chunk_id if index < len(candidate_chunks) else None,
        })

    candidate_records = [
        {"chunk_id": chunk.chunk_id, "text": chunk.text}
        for chunk in candidate_chunks
    ]
    canonical_fingerprint = _sha256_bytes(
        json.dumps(canonical_records, sort_keys=True, ensure_ascii=False).encode()
    )
    candidate_fingerprint = _sha256_bytes(
        json.dumps(candidate_records, sort_keys=True, ensure_ascii=False).encode()
    )
    candidate_core_records = _core_table_records(candidate_records)
    canonical_core_records = _core_table_records(canonical_records)
    counts: dict[str, int] = {}
    for classification in classifications:
        key = classification["classification"]
        counts[key] = counts.get(key, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "ticker": filing_data["ticker"],
        "root_anchor_table_count": len(tables),
        "candidate_chunk_count": len(candidate_chunks),
        "canonical_table_chunk_count": len(canonical_records),
        "candidate_matches_canonical": candidate_records == canonical_records,
        "candidate_matches_canonical_without_unit_metadata": (
            candidate_core_records == canonical_core_records
        ),
        "candidate_table_chunks_sha256": candidate_fingerprint,
        "canonical_table_chunks_sha256": canonical_fingerprint,
        "classification_counts": dict(sorted(counts.items())),
        "tables": classifications,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ticker", default="PEP")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    html_path, sections_path, chunks_path = _find_paths(
        args.ticker, settings.data_processed_dir, settings.data_raw_dir
    )
    inputs = [html_path, sections_path, chunks_path]
    before = _digest_inputs(inputs)
    report = audit_pep_root_anchor_tables(html_path, sections_path, chunks_path)
    after = _digest_inputs(inputs)
    report["read_only"] = True
    report["read_inputs_immutable"] = before == after
    report["read_inputs_sha256"] = after
    report["report_fingerprint"] = _sha256_bytes(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"{args.ticker}: tables={report['root_anchor_table_count']} "
        f"candidate_matches_canonical={report['candidate_matches_canonical']}"
    )
    return 0 if report["read_inputs_immutable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
