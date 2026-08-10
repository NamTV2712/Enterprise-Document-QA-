from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts.index_chunks import rebuild_index_with_manifest
from src.retrieval.index_manifest import load_index_manifest
from src.retrieval.vector_store import COLLECTION_NAME


def _chunk(chunk_id: str, value: float) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": f"Evidence {chunk_id}",
        "ticker": "AAPL",
        "section": "risk_factors",
        "accession_number": "filing",
        "filing_date": "2025-01-01",
        "report_date": "2024-12-31",
        "chunk_index": 0,
        "token_count": 2,
        "embedding": [value, value + 0.1],
    }


def _temporary_manifest_path() -> Path:
    return Path("tests") / f".index_build_{uuid4().hex}.json"


class _FakeClient:
    def __init__(self):
        self.deleted = []

    def get_collections(self):
        return SimpleNamespace(
            collections=[SimpleNamespace(name=COLLECTION_NAME)]
        )

    def delete_collection(self, *, collection_name):
        self.deleted.append(collection_name)


class _FakeStore:
    def __init__(self, *, points_count: int, upsert_error: Exception | None = None):
        self.client = _FakeClient()
        self.points_count = points_count
        self.upsert_error = upsert_error
        self.created_dimensions = []
        self.upserted = []

    def create_collection(self, embedding_dim: int):
        self.created_dimensions.append(embedding_dim)

    def upsert_chunks(self, chunks):
        if self.upsert_error is not None:
            raise self.upsert_error
        self.upserted.extend(chunks)

    def get_collection_info(self):
        return {"points_count": self.points_count, "status": "green"}


def _rebuild(store, chunks, manifest_path):
    return rebuild_index_with_manifest(
        store=store,
        chunks=chunks,
        manifest_path=manifest_path,
        embedding_model_id="nomic-ai/nomic-embed-text-v1.5",
        embedding_model_revision="embedding-commit",
        vector_dimension=2,
    )


def test_rebuild_publishes_manifest_only_after_verified_point_count() -> None:
    chunks = [_chunk("A", 0.1), _chunk("B", 0.2)]
    store = _FakeStore(points_count=2)
    path = _temporary_manifest_path()
    try:
        manifest = _rebuild(store, chunks, path)

        assert store.client.deleted == [COLLECTION_NAME]
        assert store.created_dimensions == [2]
        assert [chunk["chunk_id"] for chunk in store.upserted] == ["A", "B"]
        assert load_index_manifest(path) == manifest
        assert manifest["point_count"] == 2
    finally:
        path.unlink(missing_ok=True)


def test_rebuild_invalidates_old_manifest_when_index_mutation_fails() -> None:
    chunks = [_chunk("A", 0.1)]
    store = _FakeStore(points_count=0, upsert_error=RuntimeError("upsert failed"))
    path = _temporary_manifest_path()
    path.write_text('{"old": true}', encoding="utf-8")
    try:
        with pytest.raises(RuntimeError, match="upsert failed"):
            _rebuild(store, chunks, path)

        assert path.exists() is False
        assert store.client.deleted == [COLLECTION_NAME]
    finally:
        path.unlink(missing_ok=True)


def test_rebuild_does_not_publish_manifest_when_point_count_mismatches() -> None:
    chunks = [_chunk("A", 0.1), _chunk("B", 0.2)]
    store = _FakeStore(points_count=1)
    path = _temporary_manifest_path()
    try:
        with pytest.raises(ValueError, match="point count"):
            _rebuild(store, chunks, path)

        assert path.exists() is False
    finally:
        path.unlink(missing_ok=True)


def test_invalid_provenance_fails_before_collection_or_manifest_mutation() -> None:
    chunks = [_chunk("A", 0.1)]
    store = _FakeStore(points_count=1)
    path = _temporary_manifest_path()
    path.write_text("trusted-old-manifest", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="embedding_model_revision"):
            rebuild_index_with_manifest(
                store=store,
                chunks=chunks,
                manifest_path=path,
                embedding_model_id="nomic-ai/nomic-embed-text-v1.5",
                embedding_model_revision="",
                vector_dimension=2,
            )

        assert path.read_text(encoding="utf-8") == "trusted-old-manifest"
        assert store.client.deleted == []
        assert store.created_dimensions == []
    finally:
        path.unlink(missing_ok=True)

