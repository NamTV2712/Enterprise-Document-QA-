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
import re
import threading
import time

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from src.retrieval.embedder import AUTO_DEVICE, Embedder, resolve_torch_device
from src.retrieval.lexical_ladder import lexical_ladder_candidates
from src.retrieval.query_shaper import shape_retrieval_query
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.structured_lookup import StructuredMatch, structured_lookup
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CROSS_ENCODER_MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
CROSS_ENCODER_BATCH_SIZE = 4
RRF_K = 60  # The RRF constant, 60, is a commonly observed empirical value
CE_RELATIVE_CUTOFF = 0.50


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


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


def _promote_structured_match(
    reranked: list[tuple[dict, float]],
    structured_match: StructuredMatch,
    top_k: int,
    backup_chunks: int = 1,
) -> list[tuple[dict, float]]:
    """Put a high-confidence structured match first and keep minimal backup context."""
    matched_id = structured_match.chunk["chunk_id"]
    remaining = [
        (chunk, score)
        for chunk, score in reranked
        if chunk["chunk_id"] != matched_id
    ]
    limit = max(1, min(top_k, 1 + backup_chunks))
    return [(structured_match.chunk, 10.0), *remaining[: limit - 1]]


class HybridRetriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        all_chunks: list[dict],
        device: str = AUTO_DEVICE,
        cross_encoder_model: str = CROSS_ENCODER_MODEL,
        cross_encoder_revision: str = CROSS_ENCODER_MODEL_REVISION,
    ):
        self.embedder = embedder
        self.store = store
        self.device = resolve_torch_device(device)
        self._all_chunks = all_chunks
        self._chunks_by_id = {c["chunk_id"]: c for c in all_chunks}
        self._chunk_index_map = {c["chunk_id"]: i for i, c in enumerate(all_chunks)}

        # Pre-build per-ticker and per-section indexes for O(1) filtering
        self._chunks_by_ticker: dict[str, list[dict]] = {}
        self._chunks_by_section: dict[str, list[dict]] = {}
        self._chunks_by_ticker_section: dict[tuple[str, str], list[dict]] = {}
        for c in all_chunks:
            ticker = c["ticker"]
            section = c["section"]
            if ticker not in self._chunks_by_ticker:
                self._chunks_by_ticker[ticker] = []
            self._chunks_by_ticker[ticker].append(c)
            if section not in self._chunks_by_section:
                self._chunks_by_section[section] = []
            self._chunks_by_section[section].append(c)
            key = (ticker, section)
            if key not in self._chunks_by_ticker_section:
                self._chunks_by_ticker_section[key] = []
            self._chunks_by_ticker_section[key].append(c)

        # Build BM25 index
        logger.info("Building BM25 index on %d chunks", len(all_chunks))
        tokenized = [_tokenize(c["text"]) for c in all_chunks]
        self.bm25 = BM25Okapi(tokenized)

        # Load cross-encoder
        logger.info(
            "Loading cross-encoder: %s (revision=%s) on %s",
            cross_encoder_model,
            cross_encoder_revision or "unversioned",
            self.device,
        )
        self.cross_encoder_model = cross_encoder_model
        self.cross_encoder_revision = cross_encoder_revision
        self.cross_encoder = CrossEncoder(
            cross_encoder_model,
            revision=cross_encoder_revision or None,
            device=self.device,
        )
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
        use_lexical_ladder: bool = True,
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
            use_lexical_ladder=use_lexical_ladder,
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
        use_lexical_ladder: bool = True,
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
            use_lexical_ladder=use_lexical_ladder,
        )

        return self._format_results(query, reranked)

    def inspect(
        self,
        query: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        candidate_pool: int = 10,
        preset: str = "hybrid_rerank",
    ) -> dict:
        """Return a provider-free trace of the retrieval stages.

        This is intentionally separate from production retrieval. It exposes
        raw stage scores with their original scale and never labels them as a
        confidence value. The production path remains byte-compatible because
        this method does not alter ``retrieve_with_embedding``.
        """
        allowed_presets = {"bm25", "dense", "hybrid", "hybrid_rerank"}
        if preset not in allowed_presets:
            raise ValueError(f"unsupported retrieval preset: {preset}")
        if not query.strip():
            return {"preset": preset, "query": query, "candidates": [], "selected_chunk_ids": []}
        top_k = max(1, min(top_k, 10))
        candidate_pool = max(top_k, min(candidate_pool, 50))
        trace_started = time.perf_counter()
        query_embedding = self.embed_query(query)
        embedding_ms = (time.perf_counter() - trace_started) * 1000

        if ticker and section:
            filtered_chunks = self._chunks_by_ticker_section.get((ticker, section), [])
        elif ticker:
            filtered_chunks = self._chunks_by_ticker.get(ticker, [])
        elif section:
            filtered_chunks = self._chunks_by_section.get(section, [])
        else:
            filtered_chunks = self._all_chunks

        stage_started = time.perf_counter()
        bm25_scores = self.bm25.get_scores(_tokenize(query))
        bm25_candidates = sorted(
            filtered_chunks,
            key=lambda chunk: bm25_scores[self._chunk_index_map[chunk["chunk_id"]]],
            reverse=True,
        )[:candidate_pool]
        bm25_ids = [chunk["chunk_id"] for chunk in bm25_candidates]
        bm25_ms = (time.perf_counter() - stage_started) * 1000

        stage_started = time.perf_counter()
        semantic_results = self.store.search(
            query_vector=query_embedding,
            top_k=candidate_pool,
            ticker=ticker,
            section=section,
        )
        dense_scores = {
            result["chunk_id"]: float(result.get("score", 0.0))
            for result in semantic_results
        }
        dense_ids = [result["chunk_id"] for result in semantic_results]
        dense_ms = (time.perf_counter() - stage_started) * 1000

        stage_started = time.perf_counter()
        hints = shape_retrieval_query(query)
        lexical_ids = [
            match.chunk["chunk_id"]
            for match in lexical_ladder_candidates(
                filtered_chunks,
                ticker=ticker,
                section=section,
                exact_phrases=hints.exact_phrases,
                full_terms=hints.full_terms,
                partial_terms=hints.partial_terms,
                fuzzy_terms=hints.fuzzy_terms,
                max_candidates=candidate_pool,
            )
        ]
        lexical_rank = {chunk_id: rank + 1 for rank, chunk_id in enumerate(lexical_ids)}
        lexical_ms = (time.perf_counter() - stage_started) * 1000

        rrf_scores: dict[str, float] = {}
        for ids in (bm25_ids, dense_ids, lexical_ids):
            for rank, chunk_id in enumerate(ids):
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1 / (RRF_K + rank + 1)
        hybrid_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:candidate_pool]
        hybrid_chunks = [self._chunks_by_id[chunk_id] for chunk_id in hybrid_ids]

        cross_encoder_scores: dict[str, float] = {}
        if preset == "hybrid_rerank":
            stage_started = time.perf_counter()
            pairs = [(query, chunk["text"]) for chunk in hybrid_chunks]
            with self._model_lock:
                scores = self.cross_encoder.predict(pairs, batch_size=CROSS_ENCODER_BATCH_SIZE)
            cross_encoder_scores = {
                chunk["chunk_id"]: float(score)
                for chunk, score in zip(hybrid_chunks, scores)
            }
            final_ids = [
                chunk["chunk_id"]
                for chunk in sorted(
                    hybrid_chunks,
                    key=lambda chunk: cross_encoder_scores[chunk["chunk_id"]],
                    reverse=True,
                )[:top_k]
            ]
            rerank_ms = (time.perf_counter() - stage_started) * 1000
        elif preset == "bm25":
            final_ids = bm25_ids[:top_k]
            rerank_ms = 0.0
        elif preset == "dense":
            final_ids = dense_ids[:top_k]
            rerank_ms = 0.0
        else:
            final_ids = hybrid_ids[:top_k]
            rerank_ms = 0.0

        all_ids = list(dict.fromkeys((*bm25_ids, *dense_ids, *lexical_ids, *hybrid_ids)))
        bm25_rank = {chunk_id: rank + 1 for rank, chunk_id in enumerate(bm25_ids)}
        dense_rank = {chunk_id: rank + 1 for rank, chunk_id in enumerate(dense_ids)}
        final_rank = {chunk_id: rank + 1 for rank, chunk_id in enumerate(final_ids)}
        candidates = []
        for chunk_id in all_ids[:candidate_pool]:
            chunk = self._chunks_by_id[chunk_id]
            candidates.append(
                {
                    "chunk_id": chunk_id,
                    "ticker": chunk.get("ticker"),
                    "section": chunk.get("section"),
                    "filing_date": chunk.get("filing_date"),
                    "citation": RetrievedChunk.from_raw(chunk, score=0.0).citation,
                    "text_preview": chunk.get("text", "")[:240],
                    "bm25_score": round(float(bm25_scores[self._chunk_index_map[chunk_id]]), 6)
                    if chunk_id in bm25_rank else None,
                    "bm25_rank": bm25_rank.get(chunk_id),
                    "dense_score": round(dense_scores[chunk_id], 6)
                    if chunk_id in dense_scores else None,
                    "dense_rank": dense_rank.get(chunk_id),
                    "lexical_rank": lexical_rank.get(chunk_id),
                    "rrf_score": round(rrf_scores[chunk_id], 8) if chunk_id in rrf_scores else None,
                    "cross_encoder_score": round(cross_encoder_scores[chunk_id], 6)
                    if chunk_id in cross_encoder_scores else None,
                    "final_rank": final_rank.get(chunk_id),
                    "selected": chunk_id in final_rank,
                }
            )

        return {
            "preset": preset,
            "query": query,
            "filters": {"ticker": ticker, "section": section},
            "top_k": top_k,
            "candidate_pool": candidate_pool,
            "models": {
                "embedding": getattr(self.embedder, "model_name", None),
                "reranker": self.cross_encoder_model if preset == "hybrid_rerank" else None,
                "rrf_k": RRF_K,
            },
            "stages": [
                {"name": "embedding", "elapsed_ms": round(embedding_ms, 3)},
                {"name": "bm25", "elapsed_ms": round(bm25_ms, 3)},
                {"name": "dense", "elapsed_ms": round(dense_ms, 3)},
                {"name": "lexical_ladder", "elapsed_ms": round(lexical_ms, 3)},
                {"name": "reranker", "elapsed_ms": round(rerank_ms, 3), "skipped": preset != "hybrid_rerank"},
            ],
            "candidates": candidates,
            "selected_chunk_ids": final_ids,
            "elapsed_ms": round((time.perf_counter() - trace_started) * 1000, 3),
        }

    def _retrieve_with_embedding(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
        candidate_pool: int = 10,
        use_lexical_ladder: bool = True,
    ) -> list[tuple[dict, float]]:
        """Run retrieval with model lock scoped only to cross-encoder inference."""
        structured_match = None
        if section in (None, "financial_table", "financial_statements"):
            structured_match = structured_lookup(query, ticker, self._all_chunks)

        # --- Stage 1: BM25 search ---
        bm25_scores = self.bm25.get_scores(_tokenize(query))
        # Apply filter using pre-built indexes for O(1) lookup when available
        if hasattr(self, "_chunks_by_ticker_section"):
            if ticker and section:
                filtered_chunks = self._chunks_by_ticker_section.get((ticker, section), [])
            elif ticker:
                filtered_chunks = self._chunks_by_ticker.get(ticker, [])
            elif section:
                filtered_chunks = self._chunks_by_section.get(section, [])
            else:
                filtered_chunks = self._all_chunks
        else:
            # Fallback for tests that bypass __init__
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

        lexical_ids: list[str] = []
        if use_lexical_ladder:
            hints = shape_retrieval_query(query)
            lexical_ids = [
                match.chunk["chunk_id"]
                for match in lexical_ladder_candidates(
                    filtered_chunks,
                    ticker=ticker,
                    section=section,
                    exact_phrases=hints.exact_phrases,
                    full_terms=hints.full_terms,
                    partial_terms=hints.partial_terms,
                    fuzzy_terms=hints.fuzzy_terms,
                    max_candidates=candidate_pool,
                )
            ]

        # --- Stage 3: RRF merge ---
        bm25_ids = [c["chunk_id"] for c in bm25_candidates]
        rrf_scores: dict[str, float] = {}

        for rank, chunk_id in enumerate(bm25_ids):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        for rank, chunk_id in enumerate(semantic_ids):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank + 1)
        for rank, chunk_id in enumerate(lexical_ids):
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

        if (
            structured_match is not None
            and section is not None
            and structured_match.chunk.get("section") != section
        ):
            logger.debug(
                "Discarding structured match from section=%s for explicit section=%s",
                structured_match.chunk.get("section"),
                section,
            )
            structured_match = None

        if structured_match is not None:
            matched_id = structured_match.chunk["chunk_id"]
            reranked = _promote_structured_match(reranked, structured_match, top_k)
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
            result.append(RetrievedChunk.from_raw(chunk, score=ce_score))
        logger.info(
            "HybridRetriever: '%s...' -> %d chunks (top CE score: %.4f)",
            query[:50], len(result), result[0].score if result else 0
        )
        return result
