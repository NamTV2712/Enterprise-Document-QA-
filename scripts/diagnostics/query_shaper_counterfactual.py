"""Compare an original retrieval query with deterministic filing hints."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from configs.offline_guard import offline_socket_guard
from configs.settings import settings
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_shaper import shape_retrieval_query
from src.retrieval.vector_store import VectorStore


DEFAULT_QUERY = "Amazon AWS growth"
REQUIRED_VALUES = ("107,556", "128,725")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-pool", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    shaped = shape_retrieval_query(args.query)

    with offline_socket_guard():
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
            comparisons = []
            for label, query in (("original", args.query), ("shaped", shaped.retrieval_query)):
                started = time.perf_counter()
                results = retriever.retrieve(
                    query=query,
                    top_k=args.top_k,
                    ticker="AMZN",
                    section=None,
                    candidate_pool=args.candidate_pool,
                )
                comparisons.append({
                    "label": label,
                    "query": query,
                    "elapsed_seconds": round(time.perf_counter() - started, 4),
                    "required_value_hits": {
                        value: any(value in chunk.text for chunk in results)
                        for value in REQUIRED_VALUES
                    },
                    "results": [
                        {
                            "rank": rank,
                            "chunk_id": chunk.chunk_id,
                            "score": round(chunk.score, 4),
                            "section": chunk.section,
                            "text_preview": " ".join(chunk.text.split())[:220],
                        }
                        for rank, chunk in enumerate(results, 1)
                    ],
                })

    report = {
        "schema_version": 1,
        "query": args.query,
        "shaped_query": shaped.retrieval_query,
        "exact_phrases": shaped.exact_phrases,
        "full_terms": shaped.full_terms,
        "comparisons": comparisons,
        "passed": all(
            all(item["required_value_hits"].values())
            for item in comparisons if item["label"] == "shaped"
        ),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
