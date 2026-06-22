"""
Module: vector_store.py
Purpose: A wrapper for Qdrant — creating collections, upsert chunks, semantic search.
Designed to be easily ported from a local persistent server to the Qdrant server
simply by changing initialization parameters, without modifying business logic.
"""

import logging
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sec_filings"
BATCH_SIZE = 100


class VectorStore:
    def __init__(self, path: str | Path = "data/qdrant"):
        """Local persistent mode: data is saved to disk and remains after restarting.
            To switch to Qdrant server: replace with
            QdrantClient(host="localhost", port=6333)
            — the rest of the class remains unchanged.
        """
        Path(path).mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(path))
        logger.info("Qdrant client initialized at: %s", path)

    def create_collection(self, embedding_dim: int = 768) -> None:
        """Create collection if it doesn't exist.
        If it already exists, skip — idempotent, safe to call multiple times.
        """
        existing = [c.name for c in self.client.get_collections().collections]
        if COLLECTION_NAME in existing:
            logger.info("Collection '%s' already exists, skipping.", COLLECTION_NAME)
            return

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
        )
        logger.info("Created collection '%s' (dim=%d, Cosine)", COLLECTION_NAME, embedding_dim)

    def upsert_chunks(self, chunks: list[dict]) -> None:
        """Upsert list of chunks from embedded JSONL.

        Uses a deterministic UUID derived from chunk_id, so rerunning indexing
        updates existing points instead of creating duplicates across processes.
        """
        points = [
            PointStruct(
                id=self._chunk_id_to_uuid(c["chunk_id"]),
                vector=c["embedding"],
                payload={
                    "chunk_id": c["chunk_id"],
                    "ticker": c["ticker"],
                    "section": c["section"],
                    "accession_number": c["accession_number"],
                    "filing_date": c["filing_date"],
                    "report_date": c["report_date"],
                    "chunk_index": c["chunk_index"],
                    "token_count": c["token_count"],
                    "text": c["text"],
                },
            )
            for c in chunks
        ]
        for start in range(0, len(points), BATCH_SIZE):
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=points[start:start + BATCH_SIZE],
            )
        logger.info("Upserted %d points into collection '%s'", len(points), COLLECTION_NAME)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
    ) -> list[dict]:
        """Semantic search supports filtering by ticker and/or section.
            Returns a list dict with the fields 'score' (0-1), 'text', and all metadata.
        """
        query_filter = self._build_filter(ticker=ticker, section=section)
        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        results = response.points
        return [{"score": r.score, **r.payload} for r in results]

    def get_collection_info(self) -> dict:
        info = self.client.get_collection(COLLECTION_NAME)
        return {
            "vectors_count": getattr(info, "vectors_count", info.points_count),
            "indexed_vectors_count": getattr(info, "indexed_vectors_count", None),
            "points_count": info.points_count,
            "status": str(info.status),
        }

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "VectorStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _chunk_id_to_uuid(chunk_id: str) -> str:
        """Qdrant accepts UUID strings; uuid5 is stable across Python processes."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

    @staticmethod
    def _build_filter(
        ticker: str | None, section: str | None
    ) -> Filter | None:
        conditions = []
        if ticker:
            conditions.append(FieldCondition(key="ticker", match=MatchValue(value=ticker)))
        if section:
            conditions.append(FieldCondition(key="section", match=MatchValue(value=section)))
        return Filter(must=conditions) if conditions else None
