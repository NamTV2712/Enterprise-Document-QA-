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
import threading
from pathlib import Path

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from src.retrieval.embedder import AUTO_DEVICE, Embedder, resolve_torch_device
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.structured_lookup import structured_lookup
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CROSS_ENCODER_BATCH_SIZE = 4
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


def _select_adaptive_chunks(
    reranked: list[tuple[dict, float]],
    max_k: int = 5,
    min_k: int = 1,
    gap_threshold: float = 1.0,
) -> list[tuple[dict, float]]:
    """Select chunks by cutting at a large cross-encoder score drop.

    This is intentionally an experimental helper and is not wired into normal
    retrieval yet. It supports offline validation of whether score gaps can
    reduce low-value context without hurting deterministic recall proxies.
    """
    if not reranked:
        return []

    selected = [reranked[0]]
    for index in range(1, min(len(reranked), max_k)):
        gap = reranked[index - 1][1] - reranked[index][1]
        if len(selected) >= min_k and gap > gap_threshold:
            break
        selected.append(reranked[index])
    return selected


class HybridRetriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        all_chunks: list[dict],
        device: str = AUTO_DEVICE,
    ):
        self.embedder = embedder
        self.store = store
        self.device = resolve_torch_device(device)
        self._all_chunks = all_chunks
        self._chunks_by_id = {c["chunk_id"]: c for c in all_chunks}
        self._chunk_index_map = {c["chunk_id"]: i for i, c in enumerate(all_chunks)}

        # Build BM25 index
        logger.info("Building BM25 index on %d chunks", len(all_chunks))
        tokenized = [_tokenize(c["text"]) for c in all_chunks]
        self.bm25 = BM25Okapi(tokenized)

        # Load cross-encoder
        logger.info("Loading cross-encoder: %s on %s", CROSS_ENCODER_MODEL, self.device)
        self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL, device=self.device)
        # Protect shared model instances for every retrieval path, including
        # direct queries, streaming queries, and decomposed sub-queries.
        self._model_lock = threading.Lock()
        logger.info("HybridRetriever ready")

    def embed_query(self, query: str) -> list[float]:
        """Embed a query through the shared retriever model lock."""
        with self._model_lock:
            return self.embedder.embed_query(query)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        candidate_pool: int = 10,
    ) -> list[RetrievedChunk]:
        """Backward-compatible wrapper that embeds the query before retrieval."""
        if not query.strip():
            return []

        query_embedding = self.embed_query(query)
        reranked = self._retrieve_with_embedding(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            ticker=ticker,
            section=section,
            candidate_pool=candidate_pool,
        )

        return self._format_results(query, reranked)

    def retrieve_with_embedding(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        candidate_pool: int = 10,
    ) -> list[RetrievedChunk]:
        """Retrieve using a pre-computed query embedding.

        This is used by the cache-aware pipeline to avoid embedding the same
        query twice on cache misses.
        """
        if not query.strip():
            return []

        reranked = self._retrieve_with_embedding(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            ticker=ticker,
            section=section,
            candidate_pool=candidate_pool,
        )

        return self._format_results(query, reranked)

    def _retrieve_with_embedding(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        candidate_pool: int = 10,
    ) -> list[tuple[dict, float]]:
        """Run retrieval with model lock scoped only to cross-encoder inference."""
        structured_match = None
        if section in (None, "financial_table", "financial_statements"):
            structured_match = structured_lookup(query, ticker, self._all_chunks)

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
            key=lambda c: bm25_scores[self._chunk_index_map[c["chunk_id"]]],
            reverse=True
        )[:candidate_pool]

        semantic_results = self.store.search(
            query_vector=query_embedding,
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
        with self._model_lock:
            ce_scores = self.cross_encoder.predict(pairs, batch_size=CROSS_ENCODER_BATCH_SIZE)

        reranked = sorted(
            zip(top_candidates, ce_scores),
            key=lambda x: x[1],
            reverse=True
        )

        if reranked and reranked[0][1] > 0:
            cutoff = reranked[0][1] * CE_RELATIVE_CUTOFF
            reranked = [(chunk, score) for chunk, score in reranked if score >= cutoff]

        if structured_match is not None:
            matched_id = structured_match.chunk["chunk_id"]
            reranked = [
                (chunk, score)
                for chunk, score in reranked
                if chunk["chunk_id"] != matched_id
            ]
            reranked.insert(0, (structured_match.chunk, 10.0))
            logger.info(
                "Structured lookup matched %s row '%s' in %s",
                structured_match.canonical_key,
                structured_match.label,
                matched_id,
            )

        reranked = reranked[:top_k]
        return reranked

    def _format_results(
        self,
        query: str,
        reranked: list[tuple[dict, float]],
    ) -> list[RetrievedChunk]:
        result = []
        for chunk, ce_score in reranked:
            result.append(self._to_retrieved_chunk(chunk, ce_score))
        logger.info(
            "HybridRetriever: '%s...' -> %d chunks (top CE score: %.4f)",
            query[:50], len(result), result[0].score if result else 0
        )
        return result

    @staticmethod
    def _to_retrieved_chunk(chunk: dict, ce_score: float) -> RetrievedChunk:
        section_label = chunk["section"].replace("_", " ").title()
        citation = (
            f"{chunk['ticker']} 10-K (filed {chunk['filing_date']}), "
            f"Section: {section_label}"
        )
        return RetrievedChunk(
            chunk_id=chunk["chunk_id"],
            ticker=chunk["ticker"],
            section=chunk["section"],
            filing_date=chunk["filing_date"],
            score=float(ce_score),
            text=chunk["text"],
            citation=citation,
        )
