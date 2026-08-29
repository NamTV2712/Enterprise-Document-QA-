"""Evaluation Phase 1: deterministic offline retrieval artifact.

Executes the frozen retrieval plans (derived from the official N=30
artifact) against the trusted local index and writes a canonical JSON
artifact for the two-phase pipeline:

    python -m scripts.run_evaluation_phase1 --priority 2 \
        --output data/eval_artifacts/phase1_priority2.json \
        --verify-determinism

The run installs the shared offline socket guard by default, so any
accidental provider call fails immediately. Plans are mandatory: a
missing plan aborts instead of invoking an LLM planner or rewriter.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

from configs.offline_guard import offline_socket_guard
from configs.settings import settings
from scripts.diagnostics.replay_contract import (
    EvaluationReplayPlan,
    build_replay_plan_from_evaluation_record,
)
from src.evaluation.frozen_plan_overrides import (
    OVERRIDE_QUESTION,
    apply_frozen_plan_overrides,
)
from src.evaluation.retrieval_artifact import (
    CaseRetrievalResult,
    QueryRetrievalResult,
    build_retrieval_artifact,
    canonical_json,
    execute_case_retrieval,
    write_artifact,
)
from src.evaluation.retrieval_plan import (
    PlanQuery,
    RetrievalPlan,
    validate_plan_filters,
    validate_plans_cover,
)
from src.evaluation.test_set import TEST_SET
from src.memory.query_rewriter import needs_financial_expansion
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OFFICIAL_ARTIFACT_PATH = Path("data/evaluation_results_v2.json")
SUPPORTED_SECTIONS = {
    "business",
    "risk_factors",
    "mdna",
    "financial_statements",
    "financial_table",
}


def load_fixed_plans(
    official_artifact_path: Path,
    selected_questions: set[str],
) -> list[RetrievalPlan]:
    """Derive frozen plans from the official artifact; fail on gaps."""
    if not official_artifact_path.exists():
        raise FileNotFoundError(
            f"Official evaluation artifact not found: {official_artifact_path}. "
            "Fixed plans require it; refusing to run an LLM planner."
        )
    payload = json.loads(official_artifact_path.read_text(encoding="utf-8"))
    records = [
        record for record in payload.get("results", [])
        if record.get("question") in selected_questions
    ]
    record_questions = {record["question"] for record in records}
    missing_records = selected_questions - record_questions
    if missing_records:
        raise ValueError(
            f"Official artifact lacks OK records for questions: "
            f"{sorted(missing_records)}"
        )

    plans: list[RetrievalPlan] = []
    for record in records:
        replay_plan: EvaluationReplayPlan = build_replay_plan_from_evaluation_record(
            record,
            requires_rewrite=needs_financial_expansion,
            missing_rewrite_strategy="original_proxy",
        )
        plans.append(
            RetrievalPlan(
                question=replay_plan.original_question,
                category=replay_plan.category,
                route=replay_plan.route,
                queries=tuple(
                    PlanQuery(
                        effective_query=qp.effective_query,
                        ticker=qp.ticker,
                        section=qp.section,
                        query_source=qp.query_source,
                    )
                    for qp in replay_plan.query_plans
                ),
            )
        )
    return plans


def _print_stats(artifact: dict) -> None:
    fingerprints = artifact["fingerprints"]
    print("\n=== Phase 1 manifest ===")
    for name in (
        "artifact", "plan", "test_set", "corpus",
        "index_manifest", "embedding", "reranker", "query_shaper",
        "lexical_ladder", "retrieval_config",
    ):
        print(f"  {name:<16}: {fingerprints[name]}")

    routes = defaultdict(int)
    chunks_by_route = defaultdict(list)
    unique_ids: set[str] = set()
    categories = defaultdict(int)
    empty_queries = 0
    total_queries = 0
    for case in artifact["cases"]:
        routes[case["route"]] += 1
        categories[case["category"]] += 1
        case_chunk_count = len(case["final_chunk_ids"])
        chunks_by_route[case["route"]].append(case_chunk_count)
        unique_ids.update(case["final_chunk_ids"])
        for query_entry in case["queries"]:
            total_queries += 1
            if not query_entry["chunks"]:
                empty_queries += 1

    print("\n  Cases by route:")
    for route, count in sorted(routes.items()):
        sizes = chunks_by_route[route]
        avg = sum(sizes) / len(sizes) if sizes else 0.0
        print(f"    {route:<11}: {count:>3} cases, avg {avg:.2f} chunks/case")
    print("  Cases by category:")
    for category, count in sorted(categories.items()):
        print(f"    {category:<15}: {count:>3}")
    print(f"  Executed queries      : {total_queries} ({empty_queries} returned nothing)")
    print(f"  Unique chunk ids      : {len(unique_ids)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--priority", type=int, default=2)
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="Execute and serialize twice; fail unless both artifacts are byte-identical.",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Escape hatch to run without the offline socket guard (not recommended).",
    )
    parser.add_argument(
        "--official-artifact",
        type=Path,
        default=OFFICIAL_ARTIFACT_PATH,
    )
    args = parser.parse_args(argv)

    test_cases = [tc for tc in TEST_SET if tc.priority <= args.priority]
    if args.category:
        selected_categories = set(args.category)
        test_cases = [tc for tc in test_cases if tc.category in selected_categories]
    selected_questions = {tc.question for tc in test_cases}
    logger.info(
        "Phase 1 over %d/%d test cases (priority <= %d)",
        len(test_cases), len(TEST_SET), args.priority,
    )

    # Code-owned override questions have no legacy official-artifact
    # record (e.g. after the FY2024 contract rename); their plans come
    # entirely from the frozen planner snapshot.
    plans = load_fixed_plans(
        args.official_artifact, selected_questions - {OVERRIDE_QUESTION}
    )
    plans, plan_provenance = apply_frozen_plan_overrides(
        plans, selected_questions
    )
    validate_plans_cover(plans, test_cases)

    def build_once(retriever: HybridRetriever, all_chunks: list[dict]) -> dict:
        results: list[CaseRetrievalResult] = []
        plan_by_question = {plan.question: plan for plan in plans}
        for case in test_cases:
            results.append(
                execute_case_retrieval(
                    retriever=retriever,
                    case=case,
                    plan=plan_by_question[case.question],
                    top_k=5,
                )
            )
        return build_retrieval_artifact(
            test_cases=test_cases,
            plans=plans,
            results=results,
            all_chunks=all_chunks,
            top_k=5,
            plan_provenance=plan_provenance,
        )

    guard = None if args.allow_network else offline_socket_guard()
    with guard or _nullcontext():
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
            if store.mode != "local":
                raise RuntimeError(
                    "Phase 1 requires the trusted LOCAL index; cloud mode is "
                    "not verified and would also need network access."
                )
            all_chunks = load_retrieval_chunks(store, settings.data_processed_dir)
            allowed_tickers = {chunk["ticker"] for chunk in all_chunks}
            validate_plan_filters(plans, allowed_tickers, SUPPORTED_SECTIONS)

            retriever = HybridRetriever(
                embedder=embedder, store=store, all_chunks=all_chunks
            )
            logger.info("Executing frozen plans (offline guard active)...")
            artifact = build_once(retriever, all_chunks)

            if args.verify_determinism:
                logger.info("Re-executing for byte-identity verification...")
                second = build_once(retriever, all_chunks)
                if canonical_json(artifact) != canonical_json(second):
                    raise RuntimeError(
                        "Determinism check FAILED: two executions differ."
                    )
                logger.info("Determinism check PASSED (byte-identical artifacts).")

    write_artifact(artifact, args.output)
    logger.info("Artifact written: %s (%d bytes)",
                args.output, len(canonical_json(artifact)))
    _print_stats(artifact)
    return 0


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *exc_info):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
