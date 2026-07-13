"""Measure retrieval-only overhead for decomposed sub-queries.

This script does not call LLM generation, so it does not consume Groq or Gemini
quota. It compares a single retrieve() call with three concurrent retrieve()
calls, matching the shape of QueryDecomposer._execute_parallel().
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from configs.settings import settings
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.vector_store import VectorStore


BASELINE_RATIO_BEFORE_C1 = 2.98


def measure_single(retriever: HybridRetriever) -> float:
    start = time.perf_counter()
    retriever.retrieve(
        query="What is the cybersecurity risk exposure?",
        top_k=3,
        ticker="AAPL",
        section="risk_factors",
    )
    return time.perf_counter() - start


def measure_parallel_three(retriever: HybridRetriever) -> float:
    sub_queries = [
        ("What is the cybersecurity risk exposure?", "AAPL", "risk_factors"),
        ("What is the cybersecurity risk exposure?", "MSFT", "risk_factors"),
        ("What is the cybersecurity risk exposure?", "AMZN", "risk_factors"),
    ]

    def run_one(args: tuple[str, str, str]):
        query, ticker, section = args
        return retriever.retrieve(query=query, top_k=3, ticker=ticker, section=section)

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_one, sub_query) for sub_query in sub_queries]
        [future.result() for future in as_completed(futures)]
    return time.perf_counter() - start


def main() -> None:
    embedder = Embedder()
    with VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as store:
        chunks = load_embedded_chunks(settings.data_processed_dir)
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)

        # Warm up model and local indexes before measuring.
        measure_single(retriever)

        single_time = measure_single(retriever)
        print(f"Single query retrieve: {single_time:.3f}s")

        parallel_3_time = measure_parallel_three(retriever)
        print(f"3-subquery parallel retrieve: {parallel_3_time:.3f}s")

        ratio = parallel_3_time / single_time
        print(f"\nRatio (3-subquery / single): {ratio:.2f}x")
        print(f"Previous baseline before C1 fix: {BASELINE_RATIO_BEFORE_C1:.2f}x")
        improvement = "YES" if ratio < BASELINE_RATIO_BEFORE_C1 else "NO"
        direction = "lower" if ratio < BASELINE_RATIO_BEFORE_C1 else "unchanged/higher"
        print(f"Improvement: {improvement} - {direction} versus previous baseline")


if __name__ == "__main__":
    main()
