"""Snapshot and verify the canonical corpus around a financial-table rebuild."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from configs.settings import settings
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_discovery import discover_financial_tables
from src.retrieval.embedding_generation import compute_file_sha256


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _hash_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(compute_file_sha256(path).encode("ascii"))
    return f"sha256:{digest.hexdigest()}"


def _path_entry(path: Path, root: Path) -> dict[str, Any]:
    records = _load_jsonl(path)
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "file_sha256": compute_file_sha256(path),
        "record_count": len(records),
        "financial_table_count": sum(
            record.get("section") == "financial_table" for record in records
        ),
        "unit_line_count": sum(
            "\nUnits: " in f"\n{record.get('text', '')}" for record in records
        ),
    }


def _source_file_entries(root: Path, pattern: str) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "file_sha256": compute_file_sha256(path),
        }
        for path in sorted(root.glob(pattern))
    ]


def snapshot(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    chunks_root = settings.data_processed_dir
    chunk_paths = sorted(chunks_root.glob("*/*_chunks.jsonl"))
    raw_paths = sorted(settings.data_raw_dir.glob("*/*.html"))
    section_paths = sorted(chunks_root.glob("*/*_sections.json"))
    manifest_paths = [
        path
        for path in (
            settings.qdrant_index_manifest_path,
            Path("data/eval_artifacts/phase1_priority2.json"),
            Path("data/eval_artifacts/phase2_results_packed_selective_v2.json"),
        )
        if path.exists()
    ]
    active_generation = settings.embedding_generation_path
    if active_generation is None:
        raise ValueError("EMBEDDING_GENERATION_PATH must select the active generation")
    active_generation_manifest = active_generation / "embedding_generation_manifest.json"
    if not active_generation_manifest.exists():
        raise FileNotFoundError(active_generation_manifest)

    chunks_backup = output_dir / "chunks"
    for path in chunk_paths:
        target = chunks_backup / path.relative_to(chunks_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    snapshot_data = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "data_processed_dir": str(chunks_root),
        "chunk_files": [_path_entry(path, chunks_root) for path in chunk_paths],
        "raw_files": _source_file_entries(settings.data_raw_dir, "*/*.html"),
        "section_files": _source_file_entries(chunks_root, "*/*_sections.json"),
        "chunk_files_combined_sha256": _hash_paths(chunk_paths),
        "raw_files_combined_sha256": _hash_paths(raw_paths),
        "section_files_combined_sha256": _hash_paths(section_paths),
        "protected_files": [
            {
                "path": str(path),
                "file_sha256": compute_file_sha256(path),
            }
            for path in manifest_paths
        ],
        "active_generation": {
            "path": str(active_generation),
            "manifest_sha256": compute_file_sha256(active_generation_manifest),
        },
    }
    (output_dir / "snapshot.json").write_text(
        json.dumps(snapshot_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(snapshot_data, ensure_ascii=False, indent=2, sort_keys=True))


def verify(snapshot_dir: Path, output_path: Path) -> None:
    snapshot_data = json.loads((snapshot_dir / "snapshot.json").read_text(encoding="utf-8"))
    chunks_root = settings.data_processed_dir
    chunk_paths = sorted(chunks_root.glob("*/*_chunks.jsonl"))
    raw_paths = sorted(settings.data_raw_dir.glob("*/*.html"))
    section_paths = sorted(chunks_root.glob("*/*_sections.json"))

    if _hash_paths(raw_paths) != snapshot_data["raw_files_combined_sha256"]:
        raise AssertionError("Raw filing inputs changed during canonical rebuild")
    if _hash_paths(section_paths) != snapshot_data["section_files_combined_sha256"]:
        raise AssertionError("Extracted section inputs changed during canonical rebuild")

    expected_by_path = {
        entry["relative_path"]: entry for entry in snapshot_data["chunk_files"]
    }
    current_by_path = {path.relative_to(chunks_root).as_posix(): path for path in chunk_paths}
    if set(current_by_path) != set(expected_by_path):
        raise AssertionError("Canonical chunk file set changed unexpectedly")

    table_count = 0
    unit_count = 0
    changed_table_count = 0
    for relative_path, current_path in current_by_path.items():
        before_path = snapshot_dir / "chunks" / relative_path
        before = _load_jsonl(before_path)
        after = _load_jsonl(current_path)
        before_non_table = [record for record in before if record.get("section") != "financial_table"]
        after_non_table = [record for record in after if record.get("section") != "financial_table"]
        if before_non_table != after_non_table:
            raise AssertionError(f"Non-table chunks changed: {relative_path}")

        ticker = current_path.parent.name
        accession = current_path.name.removesuffix("_chunks.jsonl")
        sections_path = current_path.with_name(f"{accession}_sections.json")
        html_path = settings.data_raw_dir / ticker / f"{accession}.html"
        filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
        tables, _ = discover_financial_tables(html_path, sections_path)
        expected_tables = [
            asdict(record)
            for record in build_table_chunks(html_path, tables, filing_data)
        ]
        actual_tables = [record for record in after if record.get("section") == "financial_table"]
        if actual_tables != expected_tables:
            raise AssertionError(f"Financial-table chunks do not match fresh extraction: {relative_path}")
        table_count += len(actual_tables)
        unit_count += sum("\nUnits: " in f"\n{record.get('text', '')}" for record in actual_tables)
        changed_table_count += sum(
            before_record != after_record
            for before_record, after_record in zip(
                [record for record in before if record.get("section") == "financial_table"],
                actual_tables,
            )
        )

    protected_results = []
    index_before = None
    index_after = None
    for entry in snapshot_data["protected_files"]:
        path = Path(entry["path"])
        current_hash = compute_file_sha256(path) if path.exists() else None
        if path.name == "qdrant_index_manifest.json":
            index_before = entry["file_sha256"]
            index_after = current_hash
            continue
        protected_results.append({
            "path": str(path),
            "before_sha256": entry["file_sha256"],
            "after_sha256": current_hash,
            "unchanged": current_hash == entry["file_sha256"],
        })
        if current_hash != entry["file_sha256"]:
            raise AssertionError(f"Protected artifact changed: {path}")

    report = {
        "schema_version": 1,
        "snapshot_dir": str(snapshot_dir),
        "chunk_file_count": len(chunk_paths),
        "financial_table_count": table_count,
        "financial_table_unit_line_count": unit_count,
        "financial_table_changed_count": changed_table_count,
        "raw_inputs_unchanged": True,
        "section_inputs_unchanged": True,
        "protected_files": protected_results,
        "index_manifest": {
            "before_sha256": index_before,
            "after_sha256": index_after,
            "changed": index_before != index_after,
        },
        "canonical_chunk_files_combined_sha256": _hash_paths(chunk_paths),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--output-dir", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--snapshot-dir", type=Path, required=True)
    verify_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        snapshot(args.output_dir)
    else:
        verify(args.snapshot_dir, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
