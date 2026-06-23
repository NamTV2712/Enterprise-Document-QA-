"""
Module: hybrid_retriever.py
Upgrade the basic Retriever with:
1. BM25 keyword search in parallel with semantic search
2. Reciprocal Rank Fusion to merge two lists
3. Cross-encoder re-ranking to select top-k more accurately

Design: HybridRetriever implements the same interface as the basic Retriever
(method retrieve() returns list[RetrievedChunk]) — RAGPipeline and FastAPI
no changes needed, just swap objects.
"""

import logging
import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from src.retrieval.embedder import Embedder
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RRF_K = 60  # The RRF constant, 60, is a commonly observed empirical value
CE_RELATIVE_CUTOFF = 0.50


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def load_embedded_chunks(data_processed_dir: Path) -> list[dict]:
    chunks = []
    for path in sorted(data_processed_dir.glob("*/*_chunks_embedded.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                record.pop("embedding", None)
                chunks.append(record)
    return chunks


class HybridRetriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        all_chunks: list[dict],
    ):
        self.embedder = embedder
        self.store = store
        self._chunks_by_id = {c["chunk_id"]: c for c in all_chunks}
        self._chunk_positions = {c["chunk_id"]: i for i, c in enumerate(all_chunks)}

        # Build BM25 index
        logger.info("Building BM25 index on %d chunks", len(all_chunks))
        tokenized = [_tokenize(c["text"]) for c in all_chunks]
        self._all_chunks = all_chunks
        self.bm25 = BM25Okapi(tokenized)

        # Load cross-encoder
        logger.info("Loading cross-encoder: %s", CROSS_ENCODER_MODEL)
        self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
        logger.info("HybridRetriever ready")

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        candidate_pool: int = 20,  # number of candidates before re-ranking
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []

        # --- Stage 1: BM25 search ---
        bm25_scores = self.bm25.get_scores(_tokenize(query))
        # Apply filter for ticker/section here
        filtered_chunks = [
            c for c in self._all_chunks
            if (ticker is None or c["ticker"] == ticker)
            and (section is None or c["section"] == section)
        ]
        bm25_candidates = sorted(
            filtered_chunks,
            key=lambda c: bm25_scores[self._chunk_positions[c["chunk_id"]]],
            reverse=True
        )[:candidate_pool]

        # --- Stage 2: Semantic search ---
        query_vector = self.embedder.embed_query(query)
        semantic_results = self.store.search(
            query_vector=query_vector,
            top_k=candidate_pool,
            ticker=ticker,
            section=section,
        )
        semantic_ids = [r["chunk_id"] for r in semantic_results]

        # --- Stage 3: RRF merge ---
        bm25_ids = [c["chunk_id"] for c in bm25_candidates]
        rrf_scores: dict[str, float] = {}

        for rank, chunk_id in enumerate(bm25_ids):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        for rank, chunk_id in enumerate(semantic_ids):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)

        # Keep candidate scores rank-based because BM25 and cosine scores use different scales.
        top_candidates_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:candidate_pool]
        top_candidates = [
            self._chunks_by_id[cid]
            for cid in top_candidates_ids
            if cid in self._chunks_by_id
        ]

        # --- Stage 4: Cross-encoder re-ranking ---
        pairs = [(query, c["text"]) for c in top_candidates]
        ce_scores = self.cross_encoder.predict(pairs)

        reranked = sorted(
            zip(top_candidates, ce_scores),
            key=lambda x: x[1],
            reverse=True
        )

        if reranked and reranked[0][1] > 0:
            cutoff = reranked[0][1] * CE_RELATIVE_CUTOFF
            reranked = [(chunk, score) for chunk, score in reranked if score >= cutoff]

        reranked = reranked[:top_k]

        result = []
        for chunk, ce_score in reranked:
            section_label = chunk["section"].replace("_", " ").title()
            citation = (
                f"{chunk['ticker']} 10-K (filed {chunk['filing_date']}), "
                f"Section: {section_label}"
            )
            result.append(RetrievedChunk(
                chunk_id=chunk["chunk_id"],
                ticker=chunk["ticker"],
                section=chunk["section"],
                filing_date=chunk["filing_date"],
                score=float(ce_score),
                text=chunk["text"],
                citation=citation,
            ))
        logger.info(
            "HybridRetriever: '%s...' -> %d chunks (top CE score: %.4f)",
            query[:50], len(result), result[0].score if result else 0
        )
        return result
