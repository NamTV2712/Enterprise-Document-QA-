"""Compare fixed top-k retrieval with adaptive score-gap selection.

This script is deterministic and does not call LLM generation or judging. It
uses priority-1 evaluation cases with required keywords and reports recall proxy,
useful chunk ratio, and average selected chunk count by category.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from configs.settings import settings
from src.evaluation.evaluator import compute_recall_proxy
from src.evaluation.test_set import TEST_SET, TestCase
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import (
    HybridRetriever,
    _select_adaptive_chunks,
    load_embedded_chunks,
)
from src.retrieval.retriever import RetrievedChunk
from src.retrieval.vector_store import VectorStore


GAP_THRESHOLDS = [0.5, 1.0, 1.5, 2.0]
MAX_K = 5
CANDIDATE_POOL = 20


@dataclass
class CaseMetrics:
    category: str
    recall_proxy: float | None
    useful_chunk_ratio: float | None
    num_chunks: int


def to_retrieved_chunks(retriever: HybridRetriever, reranked: list[tuple[dict, float]]) -> list[RetrievedChunk]:
    return [retriever._to_retrieved_chunk(chunk, score) for chunk, score in reranked]


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


def evaluate_chunks(test_case: TestCase, chunks: list[RetrievedChunk]) -> CaseMetrics:
    return CaseMetrics(
        category=test_case.category,
        recall_proxy=compute_recall_proxy(test_case.required_keywords, chunks),
        useful_chunk_ratio=useful_chunk_ratio(test_case.required_keywords, chunks),
        num_chunks=len(chunks),
    )


def summarize(label: str, metrics: list[CaseMetrics]) -> None:
    grouped: dict[str, list[CaseMetrics]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.category].append(metric)

    print(f"\n=== {label} ===")
    print("category       cases  avg_chunks  recall_proxy  useful_chunk_ratio")
    for category in sorted(grouped):
        items = grouped[category]
        recalls = [item.recall_proxy for item in items if item.recall_proxy is not None]
        useful_ratios = [
            item.useful_chunk_ratio
            for item in items
            if item.useful_chunk_ratio is not None
        ]
        avg_chunks = average([float(item.num_chunks) for item in items])
        print(
            f"{category:<13} {len(items):>5}  "
            f"{format_optional(avg_chunks):>10}  "
            f"{format_optional(average(recalls)):>12}  "
            f"{format_optional(average(useful_ratios)):>18}"
        )

    recalls = [item.recall_proxy for item in metrics if item.recall_proxy is not None]
    useful_ratios = [
        item.useful_chunk_ratio
        for item in metrics
        if item.useful_chunk_ratio is not None
    ]
    avg_chunks = average([float(item.num_chunks) for item in metrics])
    print(
        f"{'ALL':<13} {len(metrics):>5}  "
        f"{format_optional(avg_chunks):>10}  "
        f"{format_optional(average(recalls)):>12}  "
        f"{format_optional(average(useful_ratios)):>18}"
    )


def main() -> None:
    test_cases = [
        test_case
        for test_case in TEST_SET
        if test_case.priority == 1 and test_case.required_keywords
    ]
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

        fixed_metrics: list[CaseMetrics] = []
        adaptive_metrics: dict[float, list[CaseMetrics]] = {
            gap: [] for gap in GAP_THRESHOLDS
        }

        for test_case in test_cases:
            query_embedding = retriever.embed_query(test_case.question)
            reranked = retriever._retrieve_with_embedding(
                query=test_case.question,
                query_embedding=query_embedding,
                top_k=CANDIDATE_POOL,
                ticker=test_case.ticker,
                section=test_case.section,
                candidate_pool=CANDIDATE_POOL,
            )

            fixed_chunks = to_retrieved_chunks(retriever, reranked[:MAX_K])
            fixed_metrics.append(evaluate_chunks(test_case, fixed_chunks))

            for gap in GAP_THRESHOLDS:
                adaptive_reranked = _select_adaptive_chunks(
                    reranked,
                    max_k=MAX_K,
                    min_k=1,
                    gap_threshold=gap,
                )
                adaptive_chunks = to_retrieved_chunks(retriever, adaptive_reranked)
                adaptive_metrics[gap].append(evaluate_chunks(test_case, adaptive_chunks))

        summarize("fixed top_k=5", fixed_metrics)
        for gap in GAP_THRESHOLDS:
            summarize(f"adaptive gap_threshold={gap}", adaptive_metrics[gap])


if __name__ == "__main__":
    main()
