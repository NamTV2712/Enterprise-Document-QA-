"""
Script: run_evaluation.py
Run the entire test set, print the results table, and save it to JSON.
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from configs.settings import settings
from src.evaluation.evaluator import (
    EvalResult,
    RAGEvaluator,
    check_fallback_correctness,
    compute_citation_correctness,
    compute_recall_proxy,
)
from src.evaluation.test_set import TEST_SET
from src.generation.generator import Generator
from src.generation.query_decomposer import QueryDecomposer
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.vector_store import VectorStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _format_optional(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def _format_bool(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    # --- Initialize pipeline ---
    embedder = Embedder()
    generator = Generator(provider="groq")

    # A production evaluation setup should use a separate judge model to reduce bias.
    judge_generator = Generator(provider="groq")
    evaluator = RAGEvaluator(judge_generator=judge_generator)

    results: list[EvalResult] = []
    rows: list[dict] = []
    fallback_checks: list[bool] = []
    with VectorStore(path=settings.data_processed_dir / "qdrant") as store:
        all_chunks = load_embedded_chunks(settings.data_processed_dir)
        logger.info("Loaded %d chunks for BM25 index", len(all_chunks))
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=all_chunks)
        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        decomposer = QueryDecomposer(pipeline=pipeline)

        for tc in TEST_SET:
            logger.info("Evaluating: %s", tc.question[:60])

            t0 = time.perf_counter()
            response = decomposer.run(
                question=tc.question,
                top_k=5,
                ticker=tc.ticker,
                section=tc.section,
            )
            latency = time.perf_counter() - t0

            judge_result = evaluator.evaluate_one(
                question=tc.question,
                answer=response.answer,
                chunks=response.all_chunks,
                ground_truth=tc.ground_truth,
            )

            citation_score = None
            if not tc.expects_fallback:
                citation_score = compute_citation_correctness(
                    response.answer,
                    len(response.all_chunks),
                )
            recall_score = compute_recall_proxy(
                tc.required_keywords,
                response.all_chunks,
            )
            fallback_ok = check_fallback_correctness(
                response.answer,
                tc.expects_fallback,
            )
            fallback_checks.append(fallback_ok)
            decomp_ok = response.was_decomposed == tc.expects_decomposition

            if tc.category == "out_of_corpus" and not fallback_ok:
                logger.warning(
                    "Out-of-corpus fallback failed for '%s'. Actual answer: %s",
                    tc.question,
                    response.answer,
                )

            result = EvalResult(
                question=tc.question,
                faithfulness=judge_result.faithfulness,
                answer_relevancy=judge_result.answer_relevancy,
                context_precision=judge_result.context_precision,
                faithfulness_reason=judge_result.faithfulness_reason,
                relevancy_reason=judge_result.relevancy_reason,
                precision_reason=judge_result.precision_reason,
                latency_seconds=round(latency, 3),
                citation_correctness=citation_score,
                recall_proxy=recall_score,
                fallback_correct=fallback_ok,
            )
            results.append(result)
            rows.append(
                {
                    "test_case": tc,
                    "result": result,
                    "answer": response.answer,
                    "was_decomposed": response.was_decomposed,
                    "decomposition_correct": decomp_ok,
                    "sub_queries": [
                        {
                            "query": sq.query,
                            "ticker": sq.ticker,
                            "section": sq.section,
                            "num_chunks": len(sq.retrieved_chunks),
                        }
                        for sq in response.sub_queries
                    ],
                }
            )

            logger.info(
                "  Faith=%.2f Relev=%.2f Prec=%.2f | Latency=%.2fs | "
                "Citation=%s | Recall=%s | FallbackOK=%s | DecompOK=%s",
                result.faithfulness,
                result.answer_relevancy,
                result.context_precision,
                result.latency_seconds,
                _format_optional(result.citation_correctness),
                _format_optional(result.recall_proxy),
                result.fallback_correct,
                decomp_ok,
            )
            time.sleep(2)

    # --- Print summary table ---
    print(f"\n{'='*110}")
    print(
        f"{'Category':<15}{'Question':<36}{'Faith':>7}{'Relev':>7}{'Prec':>7}"
        f"{'Lat(s)':>8}{'Cite':>7}{'Recall':>8}{'FB':>6}{'Decomp':>8}"
    )
    print(f"{'='*110}")
    for row in rows:
        tc = row["test_case"]
        result = row["result"]
        question = result.question[:39]
        print(
            f"{tc.category:<15}{question:<36}{result.faithfulness:>7.2f}{result.answer_relevancy:>7.2f}"
            f"{result.context_precision:>7.2f}{result.latency_seconds:>8.2f}"
            f"{_format_optional(result.citation_correctness):>7}"
            f"{_format_optional(result.recall_proxy):>8}"
            f"{_format_bool(result.fallback_correct):>6}"
            f"{_format_bool(row['decomposition_correct']):>8}"
        )

    avg_faith = sum(result.faithfulness for result in results) / len(results)
    avg_relev = sum(result.answer_relevancy for result in results) / len(results)
    avg_prec = sum(result.context_precision for result in results) / len(results)
    avg_all = sum(result.average_score for result in results) / len(results)
    avg_latency = sum(result.latency_seconds for result in results) / len(results)
    valid_citations = [
        result.citation_correctness
        for result in results
        if result.citation_correctness is not None
    ]
    valid_recalls = [
        result.recall_proxy
        for result in results
        if result.recall_proxy is not None
    ]
    avg_citation = sum(valid_citations) / len(valid_citations) if valid_citations else None
    avg_recall = sum(valid_recalls) / len(valid_recalls) if valid_recalls else None
    fallback_accuracy = sum(fallback_checks) / len(fallback_checks)

    print(f"{'='*100}")
    print("AVERAGE / SUCCESS CRITERIA CHECK:")
    print(f"  Faithfulness:          {avg_faith:.4f}  (target >=0.90)  {_pass_fail(avg_faith >= 0.90)}")
    print(f"  Answer Relevancy:      {avg_relev:.4f}")
    print(f"  Context Precision:     {avg_prec:.4f}")
    print(f"  Overall Judge Average: {avg_all:.4f}")
    print(f"  Avg Latency:           {avg_latency:.2f}s  (target <5s)  {_pass_fail(avg_latency < 5)}")
    if avg_citation is not None:
        print(
            f"  Citation Correctness:  {avg_citation:.4f}  "
            f"(target >=0.90)  {_pass_fail(avg_citation >= 0.90)}"
        )
    if avg_recall is not None:
        print(
            f"  Recall Proxy:          {avg_recall:.4f}  "
            f"(target >=0.85)  {_pass_fail(avg_recall >= 0.85)}"
        )
    print(
        f"  Fallback Accuracy:     {fallback_accuracy:.4f}  "
        f"({sum(fallback_checks)}/{len(fallback_checks)} correct)"
    )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["test_case"].category].append(row)

    print(f"\n{'='*110}")
    print("CATEGORY SUMMARY:")
    print(
        f"{'Category':<15}{'N':>4}{'Faith':>8}{'Relev':>8}{'Prec':>8}"
        f"{'Latency':>10}{'Cite':>8}{'Recall':>8}{'Fallback':>10}{'DecompOK':>10}"
    )
    print(f"{'-'*110}")
    category_summaries = {}
    for category, category_rows in sorted(grouped.items()):
        category_results = [row["result"] for row in category_rows]
        category_citations = [
            result.citation_correctness
            for result in category_results
            if result.citation_correctness is not None
        ]
        category_recalls = [
            result.recall_proxy
            for result in category_results
            if result.recall_proxy is not None
        ]
        category_fallback = _average([1.0 if result.fallback_correct else 0.0 for result in category_results])
        category_decomp = _average([1.0 if row["decomposition_correct"] else 0.0 for row in category_rows])
        summary = {
            "count": len(category_rows),
            "faithfulness": round(_average([result.faithfulness for result in category_results]), 4),
            "answer_relevancy": round(_average([result.answer_relevancy for result in category_results]), 4),
            "context_precision": round(_average([result.context_precision for result in category_results]), 4),
            "latency_seconds": round(_average([result.latency_seconds for result in category_results]), 4),
            "citation_correctness": round(_average(category_citations), 4) if category_citations else None,
            "recall_proxy": round(_average(category_recalls), 4) if category_recalls else None,
            "fallback_accuracy": round(category_fallback, 4),
            "decomposition_correct": round(category_decomp, 4),
        }
        category_summaries[category] = summary
        print(
            f"{category:<15}{summary['count']:>4}{summary['faithfulness']:>8.2f}"
            f"{summary['answer_relevancy']:>8.2f}{summary['context_precision']:>8.2f}"
            f"{summary['latency_seconds']:>10.2f}"
            f"{_format_optional(summary['citation_correctness']):>8}"
            f"{_format_optional(summary['recall_proxy']):>8}"
            f"{summary['fallback_accuracy']:>10.2f}{summary['decomposition_correct']:>10.2f}"
        )

    enumeration = category_summaries.get("enumeration")
    if enumeration:
        print(
            "\nEnumeration decomposition correctness: "
            f"{enumeration['decomposition_correct']:.4f}"
        )

    # --- Save JSON for time-series tracking ---
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": generator.model,
        "num_test_cases": len(results),
        "averages": {
            "faithfulness": round(avg_faith, 4),
            "answer_relevancy": round(avg_relev, 4),
            "context_precision": round(avg_prec, 4),
            "overall": round(avg_all, 4),
            "latency_seconds": round(avg_latency, 4),
            "citation_correctness": round(avg_citation, 4) if avg_citation is not None else None,
            "recall_proxy": round(avg_recall, 4) if avg_recall is not None else None,
            "fallback_accuracy": round(fallback_accuracy, 4),
        },
        "category_summaries": category_summaries,
        "results": [
            {
                "question": result.question,
                "category": row["test_case"].category,
                "ticker": row["test_case"].ticker,
                "section": row["test_case"].section,
                "expects_decomposition": row["test_case"].expects_decomposition,
                "was_decomposed": row["was_decomposed"],
                "decomposition_correct": row["decomposition_correct"],
                "sub_queries": row["sub_queries"],
                "answer": row["answer"],
                "faithfulness": result.faithfulness,
                "answer_relevancy": result.answer_relevancy,
                "context_precision": result.context_precision,
                "average": result.average_score,
                "latency_seconds": result.latency_seconds,
                "citation_correctness": result.citation_correctness,
                "recall_proxy": result.recall_proxy,
                "fallback_correct": result.fallback_correct,
                "reasons": {
                    "faithfulness": result.faithfulness_reason,
                    "relevancy": result.relevancy_reason,
                    "precision": result.precision_reason,
                },
            }
            for row in rows
            for result in [row["result"]]
        ],
    }
    out_path = Path("data/evaluation_results_v2.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    logger.info("Results saved to: %s", out_path)


if __name__ == "__main__":
    main()
