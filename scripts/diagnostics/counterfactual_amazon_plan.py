"""Counterfactual diagnostic: swap the AMZN subquery wording, rerun retrieval.

Tests the hypothesis that the stale llama-era subquery "Amazon total
revenue" is the root cause of the AAPL-vs-AMZN comparative retrieval
miss, by re-executing ONLY that case through pure retrieval with a
candidate subquery ("Amazon consolidated net sales") while keeping the
frozen official plans untouched.

This is a DIAGNOSTIC: nothing here freezes plans or writes official
artifacts. Output lands under data/diagnostics/.

Usage (offline model cache required):
    python -m scripts.diagnostics.counterfactual_amazon_plan
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

ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
TARGET_QUESTION = (
    "Which company, Apple or Amazon, has higher total revenue?"
)
CANDIDATE_AMZN_QUERY = "Amazon consolidated net sales"

REQUIRED_FACTS = {
    "AAPL": "391,035",
    "AMZN": "637,959",
}


def build_candidate_plan() -> RetrievalPlan:
    """Frozen plan with only the AMZN branch's effective query swapped."""
    return RetrievalPlan(
        question=TARGET_QUESTION,
        category="comparative",
        route="decomposed",
        queries=(
            PlanQuery(
                effective_query="Apple total revenue",
                ticker="AAPL",
                section="financial_statements",
                query_source="saved_subquery",
            ),
            PlanQuery(
                effective_query=CANDIDATE_AMZN_QUERY,
                ticker="AMZN",
                section="financial_statements",
                query_source="saved_subquery",
            ),
        ),
    )


def main() -> int:
    artifact_payload = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    frozen_case = next(
        c for c in artifact_payload["cases"] if c["question"] == TARGET_QUESTION
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
                retriever=retriever,
                case=test_case,
                plan=build_candidate_plan(),
                top_k=5,
            )

    print("\n=== Counterfactual result ===")
    fact_hits: dict[str, list[str]] = {"AAPL": [], "AMZN": []}
    for query_result in result.queries:
        print(f"\nQUERY: {query_result.query['effective_query']}")
        for chunk in query_result.chunks:
            ticker = chunk["chunk_id"].split("_", 1)[0]
            required = REQUIRED_FACTS.get(ticker)
            has_fact = bool(required and required in chunk["text"])
            if has_fact:
                fact_hits[ticker].append(chunk["chunk_id"])
            print(
                f"  {chunk['chunk_id'][:56]:<58} score={chunk['score']:>9} "
                f"${REQUIRED_FACTS.get(ticker, '?')}={has_fact}"
            )

    amzn_chunks = next(
        qr for qr in result.queries if qr.query["ticker"] == "AMZN"
    ).chunks
    aapl_ok = bool(fact_hits["AAPL"])
    amzn_ok = any(
        REQUIRED_FACTS["AMZN"] in chunk["text"] for chunk in amzn_chunks
    )
    passed = aapl_ok and amzn_ok

    # Re-run the auditor over the counterfactual payload.
    from scripts.diagnostics.audit_decomposed_plans import audit_decomposed_case

    candidate_payload = {
        "question": TARGET_QUESTION,
        "category": "comparative",
        "route": "decomposed",
        "queries": [
            {"query": qr.query, "chunks": qr.chunks} for qr in result.queries
        ],
        "final_chunk_ids": result.final_chunk_ids,
    }
    audit = audit_decomposed_case(
        candidate_payload,
        required_keywords=test_case.required_keywords,
        ground_truth=test_case.ground_truth,
    )
    print("\nAudit status:", audit["status"])
    print("Missing numbers:", audit["missing_ground_truth_numbers"])

    report = {
        "diagnostic": True,
        "official": False,
        "candidate_amzn_query": CANDIDATE_AMZN_QUERY,
        "passed": passed,
        "aapl_fact_hit": fact_hits["AAPL"],
        "amzn_fact_hit": [
            chunk["chunk_id"] for chunk in amzn_chunks
            if REQUIRED_FACTS["AMZN"] in chunk["text"]
        ],
        "audit_status": audit["status"],
        "audit_missing_numbers": audit["missing_ground_truth_numbers"],
        "candidate_case": candidate_payload,
        "compared_against_frozen_final_chunk_ids": frozen_case["final_chunk_ids"],
    }
    out_path = Path("data/diagnostics/counterfactual_amzn_plan.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(canonical_json(report))
    logger.info("Diagnostic written: %s", out_path)

    print(f"\nVERDICT: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
