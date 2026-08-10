"""Rebuild the local Qdrant collection from embedded JSONL artifacts."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from configs.settings import settings
from src.retrieval.index_manifest import (
    build_index_manifest,
    write_index_manifest_atomic,
)
from src.retrieval.vector_store import COLLECTION_NAME, VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

INDEX_BUILD_VERSION = "index-builder-v2-manifest"
VECTOR_DIMENSION = 768
DISTANCE_METRIC = "cosine"


class IndexStoreProtocol(Protocol):
    client: Any

    def create_collection(self, embedding_dim: int) -> None: ...

    def upsert_chunks(self, chunks: list[dict]) -> None: ...

    def get_collection_info(self) -> dict: ...


def rebuild_index_with_manifest(
    *,
    store: IndexStoreProtocol,
    chunks: Sequence[Mapping[str, Any]],
    manifest_path: Path,
    embedding_model_id: str,
    embedding_model_revision: str,
    vector_dimension: int = VECTOR_DIMENSION,
    distance_metric: str = DISTANCE_METRIC,
    build_version: str = INDEX_BUILD_VERSION,
) -> dict[str, Any]:
    """Rebuild in place and publish trust metadata only after verification.

    The collection and manifest cannot be updated in one storage transaction.
    Once index mutation starts, the old manifest is removed so a partial build
    can never retain stale trusted provenance.
    """
    proposed_manifest = build_index_manifest(
        chunks,
        collection_name=COLLECTION_NAME,
        embedding_model_id=embedding_model_id,
        embedding_model_revision=embedding_model_revision,
        vector_dimension=vector_dimension,
        distance_metric=distance_metric,
        build_version=build_version,
    )

    # Manifest invalidation is the trust boundary for the destructive rebuild.
    manifest_path.unlink(missing_ok=True)
    try:
        existing = [
            collection.name
            for collection in store.client.get_collections().collections
        ]
        if COLLECTION_NAME in existing:
            store.client.delete_collection(collection_name=COLLECTION_NAME)
            logger.info(
                "Deleted existing collection '%s' before reindexing",
                COLLECTION_NAME,
            )

        store.create_collection(embedding_dim=vector_dimension)
        store.upsert_chunks([dict(chunk) for chunk in chunks])

        info = store.get_collection_info()
        points_count = info.get("points_count")
        if points_count != len(chunks):
            raise ValueError(
                "Qdrant point count does not match index build inputs: "
                f"expected {len(chunks)}, got {points_count}"
            )
        write_index_manifest_atomic(manifest_path, proposed_manifest)
    except Exception:
        manifest_path.unlink(missing_ok=True)
        raise

    logger.info("Completed. Collection info: %s", info)
    logger.info("Published trusted index manifest: %s", manifest_path)
    return proposed_manifest


def load_embedded_index_inputs(data_processed_dir: Path) -> list[dict]:
    chunks = []
    for path in sorted(data_processed_dir.glob("*/*_chunks_embedded.jsonl")):
        with path.open(encoding="utf-8") as file:
            records = [json.loads(line) for line in file if line.strip()]
        chunks.extend(records)
        logger.info("%s: %d embedded chunks loaded", path.name, len(records))
    if not chunks:
        raise ValueError(f"No embedded chunks found in {data_processed_dir}")
    return chunks


def main() -> None:
    chunks = load_embedded_index_inputs(settings.data_processed_dir)
    with VectorStore(path=settings.qdrant_local_path) as store:
        rebuild_index_with_manifest(
            store=store,
            chunks=chunks,
            manifest_path=settings.qdrant_index_manifest_path,
            embedding_model_id=settings.embedding_model_id,
            embedding_model_revision=settings.embedding_model_revision,
        )


if __name__ == "__main__":
    main()
