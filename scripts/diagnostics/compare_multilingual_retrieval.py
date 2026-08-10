"""Compare English and Vietnamese retrieval with and without a ticker filter.

This diagnostic initializes only embedding, retrieval, and Qdrant components.
It does not instantiate the generator or call Groq.
"""

from __future__ import annotations

import sys
import time

from configs.settings import settings
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.vector_store import VectorStore


CASES = (
    ("EN / unfiltered", "How much revenue did Tesla report in 2024?", None),
    ("VI / unfiltered", "Doanh thu của Tesla năm 2024 là bao nhiêu?", None),
    ("EN / TSLA", "How much revenue did Tesla report in 2024?", "TSLA"),
    ("VI / TSLA", "Doanh thu của Tesla năm 2024 là bao nhiêu?", "TSLA"),
    ("EN canonical / unfiltered", "What was Tesla's total revenue in 2024?", None),
    ("EN canonical / TSLA", "What was Tesla's total revenue in 2024?", "TSLA"),
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    embedder = Embedder(
        model_name=settings.embedding_model_id,
        revision=settings.embedding_model_revision or None,
    )
    with VectorStore(
        mode=settings.qdrant_mode,
        path=settings.qdrant_local_path,
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as store:
        chunks = load_retrieval_chunks(store, settings.data_processed_dir)
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)

        print(f"Qdrant mode: {store.mode}")
        print(f"Indexed chunks available to BM25: {len(chunks)}")
        for label, question, ticker in CASES:
            started = time.perf_counter()
            results = retriever.retrieve(
                query=question,
                ticker=ticker,
                section=None,
                top_k=5,
                candidate_pool=10,
            )
            elapsed = time.perf_counter() - started
            tsla_count = sum(chunk.ticker == "TSLA" for chunk in results)

            print(f"\n=== {label} ===")
            print(f"question={question}")
            print(f"elapsed={elapsed:.2f}s tsla_chunks={tsla_count}/{len(results)}")
            for index, chunk in enumerate(results, 1):
                print(
                    f"  {index}. score={chunk.score:.4f} ticker={chunk.ticker} "
                    f"section={chunk.section} chunk_id={chunk.chunk_id}"
                )


if __name__ == "__main__":
    main()
