"""Compare candidate_pool sizes with deterministic retrieval metrics.

This script does not call LLM generation or judging. It measures retrieve()
latency and recall/useful-chunk proxies for priority-1 test cases with required
keywords, using the currently configured Qdrant backend.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

from configs.settings import settings
from src.evaluation.evaluator import compute_recall_proxy
from src.evaluation.test_set import TEST_SET
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.vector_store import VectorStore


POOL_SIZES = [10, 15, 20]
TOP_K = 5


@dataclass
class PoolMetric:
    category: str
    elapsed: float
    recall_proxy: float | None
    useful_chunk_ratio: float | None
    num_chunks: int


def useful_chunk_ratio(required_keywords: list[str], chunks: list[RetrievedChunk]) -> float | None:
    if not required_keywords or not chunks:
        return None
    keywords = [keyword.lower() for keyword in required_keywords]
    useful = 0
    for chunk in chunks:
        text = chunk.text.lower()
        if any(keyword in text for keyword in keywords):
            useful += 1
    return useful / len(chunks)


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def format_optional(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def summarize(pool_size: int, metrics: list[PoolMetric]) -> None:
    grouped: dict[str, list[PoolMetric]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.category].append(metric)

    print(f"\n=== candidate_pool={pool_size} ===")
    print("category       cases  avg_time_s  avg_chunks  recall_proxy  useful_chunk_ratio")
    for category in sorted(grouped):
        items = grouped[category]
        recalls = [item.recall_proxy for item in items if item.recall_proxy is not None]
        useful_ratios = [
            item.useful_chunk_ratio
            for item in items
            if item.useful_chunk_ratio is not None
        ]
        print(
            f"{category:<13} {len(items):>5}  "
            f"{format_optional(average([item.elapsed for item in items])):>10}  "
            f"{format_optional(average([float(item.num_chunks) for item in items])):>10}  "
            f"{format_optional(average(recalls)):>12}  "
            f"{format_optional(average(useful_ratios)):>18}"
        )

    recalls = [metric.recall_proxy for metric in metrics if metric.recall_proxy is not None]
    useful_ratios = [
        metric.useful_chunk_ratio
        for metric in metrics
        if metric.useful_chunk_ratio is not None
    ]
    print(
        f"{'ALL':<13} {len(metrics):>5}  "
        f"{format_optional(average([metric.elapsed for metric in metrics])):>10}  "
        f"{format_optional(average([float(metric.num_chunks) for metric in metrics])):>10}  "
        f"{format_optional(average(recalls)):>12}  "
        f"{format_optional(average(useful_ratios)):>18}"
    )


def main() -> None:
    test_cases = [
        test_case
        for test_case in TEST_SET
        if test_case.priority == 1 and test_case.required_keywords
    ]
    print(f"Qdrant mode: {settings.qdrant_mode}")
    print(f"Evaluating {len(test_cases)} priority-1 cases with required keywords")

    embedder = Embedder()
    with VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as store:
        chunks = load_embedded_chunks(settings.data_processed_dir)
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)

        # Warm up embedding and cross-encoder before timing the sweep.
        retriever.retrieve(
            query="What are Apple's main risk factors?",
            top_k=TOP_K,
            ticker="AAPL",
            section="risk_factors",
            candidate_pool=POOL_SIZES[-1],
        )

        for pool_size in POOL_SIZES:
            metrics: list[PoolMetric] = []
            for test_case in test_cases:
                start = time.perf_counter()
                retrieved_chunks = retriever.retrieve(
                    query=test_case.question,
                    top_k=TOP_K,
                    ticker=test_case.ticker,
                    section=test_case.section,
                    candidate_pool=pool_size,
                )
                elapsed = time.perf_counter() - start
                metrics.append(
                    PoolMetric(
                        category=test_case.category,
                        elapsed=elapsed,
                        recall_proxy=compute_recall_proxy(
                            test_case.required_keywords,
                            retrieved_chunks,
                        ),
                        useful_chunk_ratio=useful_chunk_ratio(
                            test_case.required_keywords,
                            retrieved_chunks,
                        ),
                        num_chunks=len(retrieved_chunks),
                    )
                )
            summarize(pool_size, metrics)


if __name__ == "__main__":
    main()
