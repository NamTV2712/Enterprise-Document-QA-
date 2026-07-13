"""Measure CrossEncoder first-call warm-up cost after model load.

This script does not call any LLM provider. It loads the cross-encoder used by
HybridRetriever and runs repeated predict() calls on ten real-sized pairs to see
whether the first request after server startup pays a significant cold-start
penalty.
"""

from __future__ import annotations

import time

from configs.settings import settings
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import (
    HybridRetriever,
    _tokenize,
    load_embedded_chunks,
)
from src.retrieval.vector_store import VectorStore


QUERY = "What are Apple's main risk factors?"
PAIR_COUNT = 10
CALLS = 5


def build_retriever_and_real_pairs() -> tuple[HybridRetriever, list[tuple[str, str]]]:
    embedder = Embedder()
    store = VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    )
    chunks = load_embedded_chunks(settings.data_processed_dir)
    retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)
    query_embedding = retriever.embed_query(QUERY)
    bm25_scores = retriever.bm25.get_scores(_tokenize(QUERY))
    filtered_chunks = [
        chunk
        for chunk in retriever._all_chunks
        if chunk["ticker"] == "AAPL" and chunk["section"] == "risk_factors"
    ]
    bm25_candidates = sorted(
        filtered_chunks,
        key=lambda chunk: bm25_scores[retriever._chunk_index_map[chunk["chunk_id"]]],
        reverse=True,
    )[:PAIR_COUNT]
    semantic_results = retriever.store.search(
        query_vector=query_embedding,
        top_k=PAIR_COUNT,
        ticker="AAPL",
        section="risk_factors",
    )
    candidate_ids = []
    for chunk in bm25_candidates:
        candidate_ids.append(chunk["chunk_id"])
    for result in semantic_results:
        if result["chunk_id"] not in candidate_ids:
            candidate_ids.append(result["chunk_id"])
    candidates = [retriever._chunks_by_id[chunk_id] for chunk_id in candidate_ids[:PAIR_COUNT]]
    return retriever, [(QUERY, chunk["text"]) for chunk in candidates]


def main() -> None:
    retriever, pairs = build_retriever_and_real_pairs()
    print(f"Using {len(pairs)} real candidate pairs")

    for index in range(1, CALLS + 1):
        start = time.perf_counter()
        retriever.cross_encoder.predict(pairs)
        elapsed = time.perf_counter() - start
        print(f"Call {index}: {elapsed:.4f}s")

    retriever.store.close()


if __name__ == "__main__":
    main()
