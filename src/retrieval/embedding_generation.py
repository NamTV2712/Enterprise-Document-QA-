"""Immutable, validated embedding generations used as trusted index inputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from src.retrieval.index_manifest import (
    compute_corpus_fingerprint,
    compute_vector_snapshot_fingerprint,
)

EMBEDDING_GENERATION_SCHEMA_VERSION = 1
EMBEDDING_GENERATION_MANIFEST_NAME = "embedding_generation_manifest.json"
GENERATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
REQUIRED_GENERATION_FIELDS = frozenset(
    {
        "schema_version",
        "generation_id",
        "status",
        "corpus_fingerprint",
        "vector_snapshot_id",
        "point_count",
        "source_file_count",
        "embedded_file_count",
        "empty_source_files",
        "files",
        "embedding_model_id",
        "embedding_model_revision",
        "vector_dimension",
        "document_prefix",
        "sentence_transformers_version",
        "torch_version",
        "compute_device",
        "torch_cuda_version",
        "embedding_dtype",
        "normalize_embeddings",
        "builder_version",
        "completed_at",
        "embedding_generation_fingerprint",
    }
)
GENERATION_METADATA_FIELDS = frozenset(
    {
        "embedding_model_id",
        "embedding_model_revision",
        "vector_dimension",
        "document_prefix",
        "sentence_transformers_version",
        "torch_version",
        "compute_device",
        "torch_cuda_version",
        "embedding_dtype",
        "normalize_embeddings",
        "builder_version",
    }
)
FINGERPRINT_EXCLUDED_FIELDS = frozenset(
    {"completed_at", "embedding_generation_fingerprint"}
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def validate_generation_id(generation_id: str) -> str:
    """Reject traversal, separators, and ambiguous directory names."""
    if (
        not isinstance(generation_id, str)
        or generation_id in {".", ".."}
        or GENERATION_ID_PATTERN.fullmatch(generation_id) is None
    ):
        raise ValueError(
            "generation_id must start with an alphanumeric character and contain "
            "only alphanumerics, '.', '_', or '-'"
        )
    return generation_id


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def compute_embedding_generation_fingerprint(
    manifest: Mapping[str, Any],
) -> str:
    deterministic = {
        key: value
        for key, value in manifest.items()
        if key not in FINGERPRINT_EXCLUDED_FIELDS
    }
    return _sha256_bytes(_canonical_json_bytes(deterministic))


def _validate_relative_path(raw_path: str) -> PurePosixPath:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("Generation file relative_path must be non-empty")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError("Generation file relative_path must stay within generation")
    if "\\" in raw_path:
        raise ValueError("Generation file relative_path must use POSIX separators")
    return path


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            records.append(record)
    return records


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                dict(value),
                temporary_file,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_jsonl_atomic(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            for record in records:
                temporary_file.write(json.dumps(dict(record), ensure_ascii=False) + "\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    missing = REQUIRED_GENERATION_FIELDS - manifest.keys()
    if missing:
        raise ValueError(
            f"Embedding generation manifest is missing fields: {sorted(missing)}"
        )
    unexpected = manifest.keys() - REQUIRED_GENERATION_FIELDS
    if unexpected:
        raise ValueError(
            f"Embedding generation manifest has unexpected fields: {sorted(unexpected)}"
        )
    if manifest.get("schema_version") != EMBEDDING_GENERATION_SCHEMA_VERSION:
        raise ValueError("Unsupported embedding generation manifest schema version")
    validate_generation_id(manifest.get("generation_id"))
    if manifest.get("status") != "complete":
        raise ValueError("Embedding generation status must be 'complete'")
    if not isinstance(manifest.get("normalize_embeddings"), bool):
        raise ValueError("normalize_embeddings must be a boolean")
    for field_name in (
        "embedding_model_id",
        "embedding_model_revision",
        "document_prefix",
        "sentence_transformers_version",
        "torch_version",
        "compute_device",
        "embedding_dtype",
        "builder_version",
        "completed_at",
    ):
        if not isinstance(manifest.get(field_name), str) or not manifest[field_name]:
            raise ValueError(f"{field_name} must be a non-empty string")
    torch_cuda_version = manifest.get("torch_cuda_version")
    if torch_cuda_version is not None and (
        not isinstance(torch_cuda_version, str) or not torch_cuda_version
    ):
        raise ValueError("torch_cuda_version must be null or a non-empty string")
    for field_name in (
        "vector_dimension",
        "point_count",
        "source_file_count",
        "embedded_file_count",
    ):
        value = manifest.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")
    if manifest["vector_dimension"] <= 0 or manifest["point_count"] <= 0:
        raise ValueError("vector_dimension and point_count must be positive")
    generation_fingerprint = manifest.get("embedding_generation_fingerprint")
    if not isinstance(generation_fingerprint, str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", generation_fingerprint
    ):
        raise ValueError("embedding_generation_fingerprint is invalid")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("Embedding generation files must be a list")
    relative_paths = []
    for file_entry in files:
        if not isinstance(file_entry, dict):
            raise ValueError("Embedding generation file entry must be an object")
        if set(file_entry) != {"relative_path", "record_count", "file_sha256"}:
            raise ValueError("Embedding generation file entry has invalid fields")
        relative_path = str(_validate_relative_path(file_entry["relative_path"]))
        if not relative_path.endswith("_chunks_embedded.jsonl"):
            raise ValueError("Embedding generation file has an invalid suffix")
        record_count = file_entry["record_count"]
        if isinstance(record_count, bool) or not isinstance(record_count, int):
            raise ValueError("Embedding generation record_count must be an integer")
        if record_count <= 0:
            raise ValueError("Embedding generation files must contain records")
        file_sha256 = file_entry["file_sha256"]
        if not isinstance(file_sha256, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", file_sha256
        ):
            raise ValueError("Embedding generation file_sha256 is invalid")
        relative_paths.append(relative_path)
    if relative_paths != sorted(relative_paths) or len(relative_paths) != len(
        set(relative_paths)
    ):
        raise ValueError("Embedding generation files must be sorted and unique")
    if manifest.get("embedded_file_count") != len(files):
        raise ValueError("embedded_file_count does not match files")


def _expected_output_paths(
    source_dir: Path,
) -> tuple[list[tuple[Path, str, list[dict[str, Any]]]], list[str]]:
    source_files = sorted(source_dir.glob("*/*_chunks.jsonl"))
    if not source_files:
        raise ValueError(f"No source chunk files found in {source_dir}")
    outputs = []
    empty_sources = []
    for source_path in source_files:
        relative_source = source_path.relative_to(source_dir).as_posix()
        records = _load_jsonl(source_path)
        if not records:
            empty_sources.append(relative_source)
            continue
        output_name = f"{source_path.stem}_embedded.jsonl"
        relative_output = (source_path.relative_to(source_dir).parent / output_name).as_posix()
        outputs.append((source_path, relative_output, records))
    return outputs, empty_sources


def _load_active_canonical_payloads(active_corpus_dir: Path) -> list[dict[str, Any]]:
    chunks = []
    for path in sorted(active_corpus_dir.glob("*/*_chunks_embedded.jsonl")):
        for record in _load_jsonl(path):
            canonical_record = dict(record)
            canonical_record.pop("embedding", None)
            chunks.append(canonical_record)
    if not chunks:
        raise ValueError(
            f"No canonical embedded payload artifacts found in {active_corpus_dir}"
        )
    return chunks


def _manifest_from_disk(
    *,
    generation_dir: Path,
    generation_id: str,
    source_dir: Path,
    metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if set(metadata) != GENERATION_METADATA_FIELDS:
        raise ValueError("Embedding generation metadata fields do not match schema")
    expected_outputs, empty_sources = _expected_output_paths(source_dir)
    expected_paths = [relative_path for _, relative_path, _ in expected_outputs]
    actual_paths = sorted(
        path.relative_to(generation_dir).as_posix()
        for path in generation_dir.glob("*/*_chunks_embedded.jsonl")
    )
    if actual_paths != expected_paths:
        raise ValueError("Generation output files do not match active source files")

    files = []
    chunks = []
    for relative_path in expected_paths:
        path = generation_dir / Path(PurePosixPath(relative_path))
        records = _load_jsonl(path)
        files.append(
            {
                "relative_path": relative_path,
                "record_count": len(records),
                "file_sha256": compute_file_sha256(path),
            }
        )
        chunks.extend(records)

    vector_dimension = metadata.get("vector_dimension")
    if isinstance(vector_dimension, bool) or not isinstance(vector_dimension, int):
        raise ValueError("vector_dimension must be an integer")
    manifest = {
        "schema_version": EMBEDDING_GENERATION_SCHEMA_VERSION,
        "generation_id": generation_id,
        "status": "complete",
        "corpus_fingerprint": compute_corpus_fingerprint(chunks),
        "vector_snapshot_id": compute_vector_snapshot_fingerprint(
            chunks,
            vector_dimension=vector_dimension,
        ),
        "point_count": len(chunks),
        "source_file_count": len(expected_outputs) + len(empty_sources),
        "embedded_file_count": len(files),
        "empty_source_files": empty_sources,
        "files": files,
        **dict(metadata),
        "completed_at": datetime.now(UTC).isoformat(),
    }
    manifest["embedding_generation_fingerprint"] = (
        compute_embedding_generation_fingerprint(manifest)
    )
    _validate_manifest_shape(manifest)
    return manifest, chunks


def build_embedding_generation(
    *,
    source_dir: Path,
    generations_root: Path,
    generation_id: str,
    embedder: Any,
    metadata: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Build a new generation and publish completion only after disk reload."""
    validate_generation_id(generation_id)
    generation_dir = generations_root / generation_id
    generation_dir.mkdir(parents=True, exist_ok=False)
    expected_outputs, _ = _expected_output_paths(source_dir)
    for _, relative_path, records in expected_outputs:
        embeddings = embedder.embed_documents([record["text"] for record in records])
        if len(embeddings) != len(records):
            raise ValueError("Embedder output count does not match input records")
        embedded_records = []
        for record, embedding in zip(records, embeddings, strict=True):
            embedded_record = dict(record)
            embedded_record["embedding"] = embedding
            embedded_records.append(embedded_record)
        write_jsonl_atomic(
            generation_dir / Path(PurePosixPath(relative_path)),
            embedded_records,
        )

    # Reload every output from disk before publishing the completion marker.
    manifest, _ = _manifest_from_disk(
        generation_dir=generation_dir,
        generation_id=generation_id,
        source_dir=source_dir,
        metadata=metadata,
    )
    _write_json_atomic(
        generation_dir / EMBEDDING_GENERATION_MANIFEST_NAME,
        manifest,
    )
    return generation_dir, manifest


def load_validated_embedding_generation(
    generation_dir: Path,
    *,
    active_corpus_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reload and verify a completed generation against active canonical corpus."""
    manifest_path = generation_dir / EMBEDDING_GENERATION_MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError("Embedding generation completion manifest is absent")
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Embedding generation manifest root must be an object")
    _validate_manifest_shape(loaded)
    if generation_dir.name != loaded["generation_id"]:
        raise ValueError("Generation directory name does not match generation_id")

    metadata = {key: loaded[key] for key in GENERATION_METADATA_FIELDS}
    recomputed, chunks = _manifest_from_disk(
        generation_dir=generation_dir,
        generation_id=loaded["generation_id"],
        source_dir=active_corpus_dir,
        metadata=metadata,
    )
    for field_name, expected_value in recomputed.items():
        if field_name == "completed_at":
            continue
        if loaded.get(field_name) != expected_value:
            raise ValueError(
                f"Embedding generation field {field_name!r} does not match disk"
            )
    expected_fingerprint = compute_embedding_generation_fingerprint(loaded)
    if loaded["embedding_generation_fingerprint"] != expected_fingerprint:
        raise ValueError("Embedding generation fingerprint does not match manifest")

    active_outputs, _ = _expected_output_paths(active_corpus_dir)
    active_chunks = [record for _, _, records in active_outputs for record in records]
    active_fingerprint = compute_corpus_fingerprint(active_chunks)
    if active_fingerprint != loaded["corpus_fingerprint"]:
        raise ValueError("Active source corpus does not match embedding generation")
    canonical_payload_fingerprint = compute_corpus_fingerprint(
        _load_active_canonical_payloads(active_corpus_dir)
    )
    if canonical_payload_fingerprint != loaded["corpus_fingerprint"]:
        raise ValueError(
            "Active canonical BM25 payload does not match embedding generation"
        )
    return chunks, loaded
