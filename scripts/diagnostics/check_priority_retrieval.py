"""Run deterministic retrieval checks for a selected evaluation priority.

This script does not call LLM generation or judging. It reports keyword recall
and top retrieved chunks for evaluation cases at one priority level.
"""

from __future__ import annotations

import argparse
import time

from configs.settings import settings
from src.evaluation.evaluator import compute_recall_proxy
from src.evaluation.test_set import TEST_SET
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.vector_store import VectorStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-pool", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    test_cases = [test_case for test_case in TEST_SET if test_case.priority == args.priority]

    print(f"Qdrant mode: {settings.qdrant_mode}")
    print(f"Evaluating {len(test_cases)} priority-{args.priority} cases")

    embedder = Embedder()
    with VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as store:
        chunks = load_embedded_chunks(settings.data_processed_dir)
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)

        recalls: list[float] = []
        for test_case in test_cases:
            start = time.perf_counter()
            retrieved_chunks = retriever.retrieve(
                query=test_case.question,
                top_k=args.top_k,
                ticker=test_case.ticker,
                section=test_case.section,
                candidate_pool=args.candidate_pool,
            )
            elapsed = time.perf_counter() - start
            recall = compute_recall_proxy(test_case.required_keywords, retrieved_chunks)
            if recall is not None:
                recalls.append(recall)

            print(f"\nQUESTION: {test_case.question}")
            print(
                f"category={test_case.category} ticker={test_case.ticker} "
                f"section={test_case.section} elapsed={elapsed:.2f}s recall={recall}"
            )
            for index, chunk in enumerate(retrieved_chunks, 1):
                text = chunk.text.replace("\n", " ")[:180]
                print(
                    f"  {index}. {chunk.chunk_id} score={chunk.score:.4f} "
                    f"ticker={chunk.ticker} section={chunk.section} text={text}"
                )

        if recalls:
            print(f"\nAverage keyword recall: {sum(recalls) / len(recalls):.4f}")


if __name__ == "__main__":
    main()
