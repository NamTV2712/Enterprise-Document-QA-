"""Counterfactual B: execute the EXACT gpt-oss planner output offline.

The live planner produced:
    AAPL "Apple total revenue"   @ financial_table
    AMZN "Amazon total revenue"  @ financial_table

If this passes, the new planner's plans are executable as-is and the
failure was stale-frozen-plan drift, not planner wording.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from configs.offline_guard import offline_socket_guard
from src.evaluation.retrieval_artifact import (
    canonical_json,
    execute_case_retrieval,
)
from src.evaluation.retrieval_plan import PlanQuery, RetrievalPlan
from src.evaluation.test_set import TEST_SET

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TARGET_QUESTION = (
    "Which company, Apple or Amazon, has higher total revenue?"
)
REQUIRED_FACTS = {"AAPL": "391,035", "AMZN": "637,959"}
OUTPUT_PATH = Path("data/diagnostics/counterfactual_planner_exact.json")


def main() -> int:
    plan = RetrievalPlan(
        question=TARGET_QUESTION,
        category="comparative",
        route="decomposed",
        queries=(
            PlanQuery(
                effective_query="Apple total revenue",
                ticker="AAPL",
                section="financial_table",
                query_source="saved_subquery",
            ),
            PlanQuery(
                effective_query="Amazon total revenue",
                ticker="AMZN",
                section="financial_table",
                query_source="saved_subquery",
            ),
        ),
    )
    test_case = next(tc for tc in TEST_SET if tc.question == TARGET_QUESTION)

    with offline_socket_guard():
        from configs.settings import settings
        from src.retrieval.chunk_loader import load_retrieval_chunks
        from src.retrieval.embedder import Embedder
        from src.retrieval.hybrid_retriever import HybridRetriever
        from src.retrieval.vector_store import VectorStore

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
            all_chunks = load_retrieval_chunks(store, settings.data_processed_dir)
            retriever = HybridRetriever(
                embedder=embedder, store=store, all_chunks=all_chunks
            )
            result = execute_case_retrieval(
                retriever=retriever, case=test_case, plan=plan, top_k=5
            )

    print("\n=== Planner-exact counterfactual ===")
    branch_hits: dict[str, bool] = {}
    for query_result in result.queries:
        ticker = query_result.query["ticker"] or ""
        required = REQUIRED_FACTS.get(ticker, "")
        hits = [
            chunk["chunk_id"] for chunk in query_result.chunks
            if required and required in chunk["text"]
        ]
        branch_hits[ticker] = bool(hits)
        print(f"\nQUERY [{ticker}] {query_result.query['effective_query']}")
        for chunk in query_result.chunks:
            marker = "HIT " if chunk["chunk_id"] in hits else "    "
            print(f"  {marker}{chunk['chunk_id'][:56]:<58} score={chunk['score']:>9}")

    passed = all(branch_hits.get(t, False) for t in ("AAPL", "AMZN"))
    print("\nbranch_hits:", branch_hits)
    print("VERDICT:", "PASS" if passed else "FAIL")

    OUTPUT_PATH.write_bytes(canonical_json({
        "diagnostic": True,
        "official": False,
        "question": TARGET_QUESTION,
        "passed": passed,
        "branch_hits": {k: v for k, v in branch_hits.items()},
        "candidate_case": {
            "question": TARGET_QUESTION,
            "category": "comparative",
            "route": "decomposed",
            "queries": [
                {"query": qr.query, "chunks": qr.chunks} for qr in result.queries
            ],
            "final_chunk_ids": result.final_chunk_ids,
        },
    }))
    logger.info("Diagnostic written: %s", OUTPUT_PATH)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
