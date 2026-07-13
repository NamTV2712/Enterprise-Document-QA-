"""Profile retrieval stages with the currently configured Qdrant backend.

This script does not call LLM generation. It measures embedding, BM25, Qdrant
search, RRF candidate merge, cross-encoder reranking, and full retrieve() using
the active settings after cloud/local configuration and concurrency changes.
"""

from __future__ import annotations

import argparse
import time

from configs.settings import settings
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import (
    CROSS_ENCODER_BATCH_SIZE,
    HybridRetriever,
    _tokenize,
    load_embedded_chunks,
)
from src.retrieval.vector_store import VectorStore


QUERY = "What are Apple's main risk factors?"
TICKER = "AAPL"
SECTION = "risk_factors"
CANDIDATE_POOL = 10
TOP_K = 5


def profile_once(retriever: HybridRetriever) -> dict[str, float]:
    timings: dict[str, float] = {}

    start = time.perf_counter()
    query_embedding = retriever.embed_query(QUERY)
    timings["embed_query"] = time.perf_counter() - start

    start = time.perf_counter()
    bm25_scores = retriever.bm25.get_scores(_tokenize(QUERY))
    filtered_chunks = [
        chunk
        for chunk in retriever._all_chunks
        if chunk["ticker"] == TICKER and chunk["section"] == SECTION
    ]
    bm25_candidates = sorted(
        filtered_chunks,
        key=lambda chunk: bm25_scores[retriever._chunk_index_map[chunk["chunk_id"]]],
        reverse=True,
    )[:CANDIDATE_POOL]
    timings["bm25_scoring"] = time.perf_counter() - start

    start = time.perf_counter()
    semantic_results = retriever.store.search(
        query_vector=query_embedding,
        top_k=CANDIDATE_POOL,
        ticker=TICKER,
        section=SECTION,
    )
    timings["qdrant_search"] = time.perf_counter() - start

    start = time.perf_counter()
    bm25_ids = [chunk["chunk_id"] for chunk in bm25_candidates]
    semantic_ids = [result["chunk_id"] for result in semantic_results]
    rrf_scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(bm25_ids):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1 / (60 + rank + 1)
    for rank, chunk_id in enumerate(semantic_ids):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1 / (60 + rank + 1)
    top_candidate_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:CANDIDATE_POOL]
    top_candidates = [
        retriever._chunks_by_id[chunk_id]
        for chunk_id in top_candidate_ids
        if chunk_id in retriever._chunks_by_id
    ]
    timings["rrf_merge"] = time.perf_counter() - start

    start = time.perf_counter()
    pairs = [(QUERY, chunk["text"]) for chunk in top_candidates]
    with retriever._model_lock:
        retriever.cross_encoder.predict(pairs, batch_size=CROSS_ENCODER_BATCH_SIZE)
    timings["cross_encoder"] = time.perf_counter() - start

    start = time.perf_counter()
    retriever.retrieve(
        query=QUERY,
        top_k=TOP_K,
        ticker=TICKER,
        section=SECTION,
        candidate_pool=CANDIDATE_POOL,
    )
    timings["total_retrieve"] = time.perf_counter() - start

    return timings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    print(f"Qdrant mode: {settings.qdrant_mode}")
    if settings.qdrant_mode == "cloud":
        print(f"Qdrant URL: {settings.qdrant_cloud_url}")
    else:
        print(f"Qdrant local path: {settings.qdrant_local_path}")

    embedder = Embedder()
    with VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as store:
        chunks = load_embedded_chunks(settings.data_processed_dir)
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)

        # Warm up models before recording measurements.
        profile_once(retriever)

        for run in range(1, args.runs + 1):
            timings = profile_once(retriever)
            print(f"\nRun {run}")
            print(f"embed_query:       {timings['embed_query']:.3f}s")
            print(f"bm25 scoring:      {timings['bm25_scoring']:.3f}s")
            print(f"qdrant search:     {timings['qdrant_search']:.3f}s")
            print(f"rrf merge:         {timings['rrf_merge']:.3f}s")
            print(f"cross_encoder:     {timings['cross_encoder']:.3f}s")
            print(f"TOTAL retrieve():  {timings['total_retrieve']:.3f}s")


if __name__ == "__main__":
    main()
