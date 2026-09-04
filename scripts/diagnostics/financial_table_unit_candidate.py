"""Build a non-destructive Phase 1 evidence-text unit candidate.

The production fix lives in the table extractor/chunker. This diagnostic
applies the same deterministic ``Units:`` enrichment to an existing frozen
Phase 1 artifact so the context and answer contracts can be checked before a
canonical corpus, embedding generation, or index rebuild is authorized.

It changes only financial-table chunk text. Retrieval order, scores, chunk
ids, citations, plans, and case membership remain unchanged. The output is a
candidate artifact and must not be treated as an official benchmark input.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import warnings
from pathlib import Path
from typing import Any

from src.evaluation.retrieval_artifact import canonical_json
from src.ingestion.table_discovery import discover_financial_tables
from src.ingestion.table_extractor import extract_table_unit


ROOT = Path(__file__).resolve().parents[2]
ENRICHMENT_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"financial-table-unit-preservation-v1-units-line-after-heading-"
    b"explicit-raw-table-evidence-only"
).hexdigest()
_CHUNK_ID_RE = re.compile(
    r"^(?P<ticker>[^_]+)_(?P<accession>\d+)_financial_table_(?P<index>\d+)$"
)


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _with_unit_line(text: str, unit: str) -> str:
    lines = text.splitlines()
    if any(line.startswith("Units:") for line in lines):
        return text
    if not lines:
        return f"Units: {unit}"
    return "\n".join([lines[0], f"Units: {unit}", *lines[1:]])


def _only_unit_line_added(before: str, after: str) -> bool:
    after_without_units = [
        line for line in after.splitlines() if not line.startswith("Units:")
    ]
    return before.splitlines() == after_without_units


def _load_raw_table(
    ticker: str,
    accession: str,
    index: int,
    cache: dict[tuple[str, str], tuple[list[Any], str]],
) -> tuple[Any | None, str | None]:
    key = (ticker, accession)
    if key not in cache:
        html_path = ROOT / f"data/raw/{ticker}/{accession}.html"
        sections_path = ROOT / f"data/processed/{ticker}/{accession}_sections.json"
        if not html_path.exists() or not sections_path.exists():
            cache[key] = ([], "missing_local_inputs")
        else:
            cache[key] = discover_financial_tables(html_path, sections_path)
    tables, _discovery_mode = cache[key]
    if index >= len(tables):
        return None, None
    return tables[index], _discovery_mode


def enrich_artifact(
    artifact: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return an enriched copy and a deterministic change report."""
    candidate = copy.deepcopy(artifact)
    source_artifact = artifact.get("fingerprints", {}).get("artifact")
    if not source_artifact:
        raise ValueError("Input artifact has no embedded artifact fingerprint")

    table_cache: dict[tuple[str, str], tuple[list[Any], str]] = {}
    chunk_texts: dict[str, str] = {}
    unit_resolution: dict[str, tuple[str | None, str | None]] = {}
    changes: list[dict[str, Any]] = []
    changed_occurrences = 0
    unchanged_financial_tables = 0
    unresolved_occurrences = 0

    for case in candidate.get("cases", []):
        for query in case.get("queries", []):
            for chunk in query.get("chunks", []):
                if chunk.get("section") != "financial_table":
                    continue
                chunk_id = chunk.get("chunk_id", "")
                before = chunk.get("text", "")
                previous_text = chunk_texts.setdefault(chunk_id, before)
                if previous_text != before:
                    raise AssertionError(
                        f"Repeated chunk {chunk_id} has inconsistent text"
                    )
                if any(line.startswith("Units:") for line in before.splitlines()):
                    unchanged_financial_tables += 1
                    continue
                if chunk_id not in unit_resolution:
                    match = _CHUNK_ID_RE.match(chunk_id)
                    if match is None:
                        unit_resolution[chunk_id] = (None, None)
                    else:
                        table, discovery_mode = _load_raw_table(
                            match.group("ticker"),
                            match.group("accession"),
                            int(match.group("index")),
                            table_cache,
                        )
                        unit_resolution[chunk_id] = (
                            extract_table_unit(table)
                            if table is not None
                            else None,
                            discovery_mode,
                        )
                unit, discovery_mode = unit_resolution[chunk_id]
                if not unit:
                    unresolved_occurrences += 1
                    continue
                after = _with_unit_line(before, unit)
                chunk["text"] = after
                changed_occurrences += 1
                if not any(row["chunk_id"] == chunk_id for row in changes):
                    changes.append(
                        {
                            "chunk_id": chunk_id,
                            "unit": unit,
                            "discovery_mode": discovery_mode,
                            "before_sha256": _sha256_text(before),
                            "after_sha256": _sha256_text(after),
                            "only_unit_line_added": _only_unit_line_added(before, after),
                        }
                    )

    changes.sort(key=lambda row: row["chunk_id"])
    if not all(row["only_unit_line_added"] for row in changes):
        raise AssertionError("Unit candidate changed a line other than Units:")

    fingerprints = candidate.setdefault("fingerprints", {})
    fingerprints["source_artifact"] = source_artifact
    fingerprints["financial_table_unit_enrichment"] = ENRICHMENT_FINGERPRINT
    fingerprints.pop("artifact", None)
    candidate.setdefault("provenance", {})[
        "financial_table_unit_enrichment"
    ] = {
        "status": "candidate_only",
        "provider_calls": 0,
        "mutated_inputs": False,
        "source_artifact": source_artifact,
        "enrichment_fingerprint": ENRICHMENT_FINGERPRINT,
        "canonical_rebuild_required": True,
    }
    fingerprints["artifact"] = _sha256_bytes(canonical_json(candidate))

    report = {
        "schema_version": 1,
        "audit": "financial_table_unit_candidate_v1",
        "provider_calls": 0,
        "mutated_inputs": False,
        "source_artifact": source_artifact,
        "candidate_artifact": fingerprints["artifact"],
        "enrichment_fingerprint": ENRICHMENT_FINGERPRINT,
        "financial_table_chunk_occurrences_changed": changed_occurrences,
        "financial_table_unique_chunks_changed": len(changes),
        "financial_table_chunk_occurrences_already_enriched": (
            unchanged_financial_tables
        ),
        "financial_table_chunk_occurrences_unresolved": unresolved_occurrences,
        "financial_table_unique_chunks_unresolved": sum(
            1 for unit, _mode in unit_resolution.values() if not unit
        ),
        "all_changes_are_unit_line_only": True,
        "changes": changes,
    }
    return candidate, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    warnings.filterwarnings("ignore", message=".*XMLParsedAsHTMLWarning.*")

    source_bytes = args.input.read_bytes()
    artifact = json.loads(source_bytes.decode("utf-8"))
    candidate, report = enrich_artifact(artifact)
    report["input_file_sha256"] = _sha256_bytes(source_bytes)
    output_bytes = canonical_json(candidate)
    report["output_file_sha256"] = _sha256_bytes(output_bytes)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output_bytes)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
