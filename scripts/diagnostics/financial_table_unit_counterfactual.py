"""Measure explicit table units lost by the current financial-table chunks.

This is a read-only counterfactual. It compares served ``financial_table``
chunks with the corresponding raw SEC table and models adding only a compact
``Units: ...`` line. It does not regenerate, delete, embed, or index data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import warnings
from pathlib import Path
from typing import Any

from src.ingestion.table_discovery import discover_financial_tables
from src.ingestion.table_extractor import extract_table_unit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "data/diagnostics/financial_table_unit_counterfactual_v1.json"
_CHUNK_ID_RE = re.compile(
    r"^(?P<ticker>[^_]+)_(?P<accession>\d+)_financial_table_(?P<index>\d+)$"
)


def _sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _with_unit_line(text: str, unit: str) -> str:
    lines = text.splitlines()
    if any(line.startswith("Units:") for line in lines):
        return text
    if not lines:
        return f"Units: {unit}"
    return "\n".join([lines[0], f"Units: {unit}", *lines[1:]])


def _only_unit_line_added(current: str, proposed: str) -> bool:
    """Check that the counterfactual preserves every existing text line."""
    current_lines = current.splitlines()
    proposed_lines = [
        line for line in proposed.splitlines() if not line.startswith("Units:")
    ]
    return current_lines == proposed_lines


def _load_table_cache(
    ticker: str,
    accession: str,
    cache: dict[tuple[str, str], tuple[list[Any], str]],
) -> tuple[list[Any], str]:
    key = (ticker, accession)
    if key not in cache:
        html_path = ROOT / f"data/raw/{ticker}/{accession}.html"
        sections_path = ROOT / f"data/processed/{ticker}/{accession}_sections.json"
        cache[key] = discover_financial_tables(html_path, sections_path)
    return cache[key]


def build_report() -> dict[str, Any]:
    table_cache: dict[tuple[str, str], tuple[list[Any], str]] = {}
    rows: list[dict[str, Any]] = []
    # Keep the explicit suffix filter so this remains deterministic on
    # Windows and ignores unrelated generated files.
    chunk_files = sorted(
        path
        for path in (ROOT / "data/processed").glob("*/*_chunks.jsonl")
        if path.is_file()
    )
    for chunk_file in chunk_files:
        for line in chunk_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            chunk = json.loads(line)
            if chunk.get("section") != "financial_table":
                continue
            chunk_id = chunk.get("chunk_id", "")
            match = _CHUNK_ID_RE.match(chunk_id)
            if match is None:
                rows.append(
                    {
                        "chunk_id": chunk_id,
                        "status": "unparseable_chunk_id",
                    }
                )
                continue
            ticker = match.group("ticker")
            accession = match.group("accession")
            index = int(match.group("index"))
            tables, discovery_mode = _load_table_cache(
                ticker, accession, table_cache
            )
            row: dict[str, Any] = {
                "chunk_id": chunk_id,
                "ticker": ticker,
                "accession": accession,
                "table_index": index,
                "discovery_mode": discovery_mode,
                "current_text_sha256": _sha256(chunk.get("text", "")),
                "current_has_unit_line": any(
                    item.startswith("Units:")
                    for item in chunk.get("text", "").splitlines()
                ),
            }
            if index >= len(tables):
                row["status"] = "raw_table_index_missing"
                rows.append(row)
                continue
            unit = extract_table_unit(tables[index])
            row.update(
                {
                    "status": "explicit_unit_found" if unit else "unit_not_found",
                    "raw_explicit_unit": unit,
                    "proposed_text_sha256": (
                        _sha256(_with_unit_line(chunk["text"], unit))
                        if unit
                        else _sha256(chunk["text"])
                    ),
                    "only_unit_line_added": bool(
                        unit
                        and _only_unit_line_added(
                            chunk["text"], _with_unit_line(chunk["text"], unit)
                        )
                    ),
                    "would_change": bool(
                        unit and not row["current_has_unit_line"]
                    ),
                }
            )
            rows.append(row)

    rows.sort(key=lambda row: row["chunk_id"])
    explicit = [row for row in rows if row.get("raw_explicit_unit")]
    changed = [row for row in rows if row.get("would_change")]
    already = [row for row in rows if row.get("current_has_unit_line")]
    return {
        "schema_version": 1,
        "audit": "financial_table_unit_counterfactual_v1",
        "provider_calls": 0,
        "mutated_inputs": False,
        "chunk_file_count": len(chunk_files),
        "table_chunk_count": len(rows),
        "raw_explicit_unit_count": len(explicit),
        "currently_embedded_unit_count": len(already),
        "candidate_changed_chunk_count": len(changed),
        "candidate_unknown_unit_count": len(
            [row for row in rows if row.get("status") == "unit_not_found"]
        ),
        "candidate_text_changes_are_unit_line_only": all(
            row.get("only_unit_line_added") is True
            for row in rows
            if row.get("status") == "explicit_unit_found"
        ),
        "chunks": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
