import json
from pathlib import Path
from uuid import uuid4

import pytest

from src.retrieval.index_manifest import (
    build_index_manifest,
    compute_corpus_fingerprint,
    compute_vector_snapshot_fingerprint,
    load_index_manifest,
    validate_index_manifest,
    write_index_manifest_atomic,
)


def _chunk(chunk_id: str, value: float, *, chunk_index: int) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": f"Evidence {chunk_id}",
        "ticker": "AAPL",
        "section": "risk_factors",
        "accession_number": "filing",
        "chunk_index": chunk_index,
        "embedding": [value, value + 0.1],
    }


def _manifest(chunks: list[dict]) -> dict:
    return build_index_manifest(
        chunks,
        generation_manifest=_generation_manifest(chunks),
        collection_name="sec_filings",
        distance_metric="cosine",
        build_version="index-builder-v1",
    )


def _generation_manifest(chunks: list[dict]) -> dict:
    return {
        "status": "complete",
        "generation_id": "generation-001",
        "embedding_generation_fingerprint": "sha256:" + "a" * 64,
        "corpus_fingerprint": compute_corpus_fingerprint(chunks),
        "vector_snapshot_id": compute_vector_snapshot_fingerprint(
            chunks, vector_dimension=2
        ),
        "point_count": len(chunks),
        "embedding_model_id": "nomic-ai/nomic-embed-text-v1.5",
        "embedding_model_revision": "embedding-commit",
        "vector_dimension": 2,
    }


def _temporary_manifest_path() -> Path:
    return Path("tests") / f".index_manifest_{uuid4().hex}.json"


def test_index_manifest_binds_corpus_and_exact_vector_build_inputs() -> None:
    chunks = [_chunk("B", 0.2, chunk_index=1), _chunk("A", 0.1, chunk_index=0)]
    manifest = _manifest(chunks)

    assert manifest["point_count"] == 2
    assert manifest["corpus_fingerprint"] == compute_corpus_fingerprint(chunks)
    assert manifest["snapshot_id"] == compute_vector_snapshot_fingerprint(
        chunks,
        vector_dimension=2,
    )
    assert manifest["embedding_model_revision"] == "embedding-commit"


def test_vector_change_changes_snapshot_but_not_corpus_fingerprint() -> None:
    first = [_chunk("A", 0.1, chunk_index=0)]
    second = [_chunk("A", 0.9, chunk_index=0)]

    assert compute_corpus_fingerprint(first) == compute_corpus_fingerprint(second)
    assert compute_vector_snapshot_fingerprint(
        first,
        vector_dimension=2,
    ) != compute_vector_snapshot_fingerprint(second, vector_dimension=2)


def test_vector_snapshot_rejects_wrong_dimension_and_non_finite_values() -> None:
    with pytest.raises(ValueError, match="dimension"):
        compute_vector_snapshot_fingerprint(
            [_chunk("A", 0.1, chunk_index=0)],
            vector_dimension=3,
        )

    invalid = _chunk("A", 0.1, chunk_index=0)
    invalid["embedding"][1] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        compute_vector_snapshot_fingerprint([invalid], vector_dimension=2)


def test_manifest_write_is_atomic_and_round_trips_through_validation() -> None:
    chunks = [_chunk("A", 0.1, chunk_index=0)]
    manifest = _manifest(chunks)
    path = _temporary_manifest_path()
    try:
        write_index_manifest_atomic(path, manifest)
        loaded = load_index_manifest(path)

        assert loaded == manifest
        validate_index_manifest(
            loaded,
            chunks,
            generation_manifest=_generation_manifest(chunks),
            collection_name="sec_filings",
            distance_metric="cosine",
            build_version="index-builder-v1",
        )
        assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
    finally:
        path.unlink(missing_ok=True)


def test_manifest_validation_detects_stale_vectors() -> None:
    original = [_chunk("A", 0.1, chunk_index=0)]
    manifest = _manifest(original)
    stale = [_chunk("A", 0.8, chunk_index=0)]

    with pytest.raises(ValueError, match="snapshot_id"):
        validate_index_manifest(
            manifest,
            stale,
            generation_manifest=_generation_manifest(original),
            collection_name="sec_filings",
            distance_metric="cosine",
            build_version="index-builder-v1",
        )


def test_manifest_loader_rejects_missing_required_provenance() -> None:
    path = _temporary_manifest_path()
    try:
        path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")

        with pytest.raises(ValueError, match="missing required fields"):
            load_index_manifest(path)
    finally:
        path.unlink(missing_ok=True)


def test_legacy_index_manifest_schema_is_not_trusted() -> None:
    path = _temporary_manifest_path()
    legacy = _manifest([_chunk("A", 0.1, chunk_index=0)])
    legacy["schema_version"] = 1
    try:
        path.write_text(json.dumps(legacy), encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported index manifest"):
            load_index_manifest(path)
    finally:
        path.unlink(missing_ok=True)
