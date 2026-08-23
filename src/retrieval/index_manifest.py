"""Trusted build manifests for deterministic Qdrant index provenance."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path
from typing import Any

from src.retrieval.canonical_json import canonical_json_bytes as _canonical_json_bytes

INDEX_MANIFEST_SCHEMA_VERSION = 2
CORPUS_FINGERPRINT_SCHEMA_VERSION = 1
VECTOR_SNAPSHOT_SCHEMA_VERSION = 1
REQUIRED_INDEX_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "collection_name",
        "corpus_fingerprint",
        "point_count",
        "embedding_model_id",
        "embedding_model_revision",
        "vector_dimension",
        "distance_metric",
        "build_version",
        "snapshot_id",
        "embedding_generation_id",
        "embedding_generation_fingerprint",
    }
)


def _sha256(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json_bytes(value)).hexdigest()}"


def _canonical_chunk_text(text: str) -> str:
    normalized_unicode = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", normalized_unicode).strip()


def _sorted_unique_chunks(chunks: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    chunks_by_id = {}
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            raise ValueError("Corpus chunk_id must be a non-empty string")
        if chunk_id in chunks_by_id:
            raise ValueError("Corpus contains duplicate chunk IDs")
        chunks_by_id[chunk_id] = chunk
    return [chunks_by_id[chunk_id] for chunk_id in sorted(chunks_by_id)]


def compute_corpus_fingerprint(chunks: Sequence[Mapping[str, Any]]) -> str:
    """Hash canonical payload identity without vectors or storage artifacts."""
    canonical_chunks = []
    for chunk in _sorted_unique_chunks(chunks):
        chunk_id = chunk["chunk_id"]
        text = chunk.get("text")
        if not isinstance(text, str):
            raise ValueError(f"Chunk {chunk_id!r} text must be a string")
        canonical = {
            "chunk_id": chunk_id,
            "text": _canonical_chunk_text(text),
        }
        for field in ("ticker", "section", "accession_number"):
            value = chunk.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"Chunk {chunk_id!r} field {field!r} must be a non-empty string"
                )
            canonical[field] = value
        chunk_index = chunk.get("chunk_index")
        if isinstance(chunk_index, bool) or not isinstance(chunk_index, int):
            raise ValueError(f"Chunk {chunk_id!r} chunk_index must be an integer")
        canonical["chunk_index"] = chunk_index
        canonical_chunks.append(canonical)
    return _sha256(
        {
            "schema_version": CORPUS_FINGERPRINT_SCHEMA_VERSION,
            "chunk_count": len(canonical_chunks),
            "chunks": canonical_chunks,
        }
    )


def compute_vector_snapshot_fingerprint(
    chunks: Sequence[Mapping[str, Any]],
    *,
    vector_dimension: int,
) -> str:
    """Hash exact vector build inputs without reading vectors back from Qdrant."""
    if isinstance(vector_dimension, bool) or vector_dimension <= 0:
        raise ValueError("vector_dimension must be a positive integer")
    sorted_chunks = _sorted_unique_chunks(chunks)
    digest = hashlib.sha256()
    digest.update(
        _canonical_json_bytes(
            {
                "schema_version": VECTOR_SNAPSHOT_SCHEMA_VERSION,
                "vector_dimension": vector_dimension,
                "point_count": len(sorted_chunks),
            }
        )
    )
    for chunk in sorted_chunks:
        chunk_id = chunk["chunk_id"]
        embedding = chunk.get("embedding")
        if not isinstance(embedding, list) or len(embedding) != vector_dimension:
            raise ValueError(
                f"Chunk {chunk_id!r} embedding dimension does not match "
                f"{vector_dimension}"
            )
        vector = []
        for value in embedding:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Chunk {chunk_id!r} embedding must be numeric")
            numeric_value = float(value)
            if not isfinite(numeric_value):
                raise ValueError(f"Chunk {chunk_id!r} embedding must contain finite values")
            vector.append(numeric_value)
        encoded_vector = _canonical_json_bytes(
            {"chunk_id": chunk_id, "embedding": vector}
        )
        digest.update(len(encoded_vector).to_bytes(8, byteorder="big"))
        digest.update(encoded_vector)
    return f"sha256:{digest.hexdigest()}"


def _required_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def build_index_manifest(
    chunks: Sequence[Mapping[str, Any]],
    *,
    generation_manifest: Mapping[str, Any],
    collection_name: str,
    distance_metric: str,
    build_version: str,
) -> dict[str, Any]:
    if not chunks:
        raise ValueError("Cannot build an index manifest for an empty corpus")
    required_generation_fields = {
        "generation_id",
        "embedding_generation_fingerprint",
        "corpus_fingerprint",
        "vector_snapshot_id",
        "point_count",
        "embedding_model_id",
        "embedding_model_revision",
        "vector_dimension",
        "status",
    }
    missing = required_generation_fields - generation_manifest.keys()
    if missing:
        raise ValueError(
            f"Embedding generation manifest is missing fields: {sorted(missing)}"
        )
    if generation_manifest.get("status") != "complete":
        raise ValueError("Embedding generation must be complete before indexing")
    vector_dimension = generation_manifest["vector_dimension"]
    expected_corpus = compute_corpus_fingerprint(chunks)
    expected_snapshot = compute_vector_snapshot_fingerprint(
        chunks,
        vector_dimension=vector_dimension,
    )
    if generation_manifest.get("point_count") != len(chunks):
        raise ValueError("Embedding generation point_count does not match chunks")
    if generation_manifest.get("corpus_fingerprint") != expected_corpus:
        raise ValueError("Embedding generation corpus_fingerprint does not match chunks")
    if generation_manifest.get("vector_snapshot_id") != expected_snapshot:
        raise ValueError("Embedding generation vector_snapshot_id does not match chunks")
    return {
        "schema_version": INDEX_MANIFEST_SCHEMA_VERSION,
        "collection_name": _required_text(
            collection_name,
            field_name="collection_name",
        ),
        "corpus_fingerprint": generation_manifest["corpus_fingerprint"],
        "point_count": len(chunks),
        "embedding_model_id": _required_text(
            generation_manifest["embedding_model_id"],
            field_name="embedding_model_id",
        ),
        "embedding_model_revision": _required_text(
            generation_manifest["embedding_model_revision"],
            field_name="embedding_model_revision",
        ),
        "vector_dimension": vector_dimension,
        "distance_metric": _required_text(
            distance_metric,
            field_name="distance_metric",
        ),
        "build_version": _required_text(build_version, field_name="build_version"),
        "snapshot_id": generation_manifest["vector_snapshot_id"],
        "embedding_generation_id": _required_text(
            generation_manifest["generation_id"],
            field_name="embedding_generation_id",
        ),
        "embedding_generation_fingerprint": _required_text(
            generation_manifest["embedding_generation_fingerprint"],
            field_name="embedding_generation_fingerprint",
        ),
    }


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    missing = REQUIRED_INDEX_MANIFEST_FIELDS - manifest.keys()
    if missing:
        raise ValueError(f"Index manifest is missing required fields: {sorted(missing)}")
    unexpected = manifest.keys() - REQUIRED_INDEX_MANIFEST_FIELDS
    if unexpected:
        raise ValueError(f"Index manifest has unexpected fields: {sorted(unexpected)}")
    if manifest.get("schema_version") != INDEX_MANIFEST_SCHEMA_VERSION:
        raise ValueError("Unsupported index manifest schema version")


def write_index_manifest_atomic(
    path: Path,
    manifest: Mapping[str, Any],
) -> None:
    """Publish a complete manifest atomically after index verification succeeds."""
    _validate_manifest_shape(manifest)
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
            json.dump(
                dict(manifest),
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


def load_index_manifest(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Index manifest root must be an object")
    _validate_manifest_shape(raw)
    return raw


def validate_index_manifest(
    manifest: Mapping[str, Any],
    chunks: Sequence[Mapping[str, Any]],
    *,
    generation_manifest: Mapping[str, Any],
    collection_name: str,
    distance_metric: str,
    build_version: str,
) -> None:
    """Recompute every trusted field from the proposed build inputs."""
    _validate_manifest_shape(manifest)
    expected = build_index_manifest(
        chunks,
        generation_manifest=generation_manifest,
        collection_name=collection_name,
        distance_metric=distance_metric,
        build_version=build_version,
    )
    for field_name, expected_value in expected.items():
        if manifest.get(field_name) != expected_value:
            raise ValueError(
                f"Index manifest field {field_name!r} does not match build inputs"
            )
