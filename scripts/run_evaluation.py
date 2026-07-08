"""
Script: run_evaluation.py
Run the test set through QueryDecomposer, checkpoint every case, print grouped results,
and save final JSON output.
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

from configs.settings import settings
from src.evaluation.evaluator import (
    RAGEvaluator,
    check_fallback_correctness,
    compute_citation_correctness,
    compute_recall_proxy,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.query_decomposer import DecomposedResponse, QueryDecomposer
from src.generation.generator import Generator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.vector_store import VectorStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CHECKPOINT_PATH = Path("data/eval_checkpoint.jsonl")
OUTPUT_PATH = Path("data/evaluation_results_v2.json")
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = [5, 15]

T = TypeVar("T")


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


def load_checkpoint() -> dict[str, dict]:
    """Load completed checkpoint records keyed by question."""
    if not CHECKPOINT_PATH.exists():
        return {}

    done = {}
    with CHECKPOINT_PATH.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("status") == "OK":
                done[record["question"]] = record

    logger.info("Checkpoint loaded: %d completed cases", len(done))
    return done


def append_checkpoint(record: dict) -> None:
    """Persist each case immediately so interrupted runs can resume safely."""
    CHECKPOINT_PATH.parent.mkdir(exist_ok=True)
    with CHECKPOINT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def call_with_capped_retry(fn: Callable[..., T], *args, **kwargs) -> tuple[T | None, str | None]:
    """Retry briefly, then return the error instead of sleeping for quota windows."""
    last_error = None
    waits = [0] + RETRY_BACKOFF_SECONDS[:MAX_RETRIES]
    for attempt, wait in enumerate(waits, start=1):
        if wait:
            time.sleep(wait)
        try:
            return fn(*args, **kwargs), None
        except Exception as e:
            last_error = str(e)
            logger.warning("Attempt %d failed: %s", attempt, last_error[:180])
    return None, last_error


def _sub_queries(response: DecomposedResponse) -> list[dict]:
    return [
        {
            "query": sq.query,
            "ticker": sq.ticker,
            "section": sq.section,
            "num_chunks": len(sq.retrieved_chunks),
        }
        for sq in response.sub_queries
    ]


def _record_success(
    tc: TestCase,
    response: DecomposedResponse,
    judge_scores,
    latency: float,
) -> dict:
    citation_score = None
    if not tc.expects_fallback:
        citation_score = compute_citation_correctness(response.answer, len(response.all_chunks))

    fallback_ok = check_fallback_correctness(response.answer, tc.expects_fallback)
    if tc.category == "out_of_corpus" and not fallback_ok:
        logger.warning(
            "Out-of-corpus fallback failed for '%s'. Actual answer: %s",
            tc.question,
            response.answer,
        )

    return {
        "question": tc.question,
        "category": tc.category,
        "ticker": tc.ticker,
        "section": tc.section,
        "status": "OK",
        "answer": response.answer,
        "faithfulness": judge_scores.faithfulness,
        "answer_relevancy": judge_scores.answer_relevancy,
        "context_precision": judge_scores.context_precision,
        "average": judge_scores.average_score,
        "latency_seconds": round(latency, 3),
        "citation_correctness": citation_score,
        "recall_proxy": compute_recall_proxy(tc.required_keywords, response.all_chunks),
        "fallback_correct": fallback_ok,
        "was_decomposed": response.was_decomposed,
        "decomposition_expected": tc.expects_decomposition,
        "decomposition_correct": response.was_decomposed == tc.expects_decomposition,
        "sub_queries": _sub_queries(response),
        "reasons": {
            "faithfulness": judge_scores.faithfulness_reason,
            "relevancy": judge_scores.relevancy_reason,
            "precision": judge_scores.precision_reason,
        },
        "timestamp": datetime.now().isoformat(),
    }


def _print_case_table(records: list[dict]) -> None:
    print(f"\n{'='*110}")
    print(
        f"{'Category':<15}{'Question':<36}{'Faith':>7}{'Relev':>7}{'Prec':>7}"
        f"{'Lat(s)':>8}{'Cite':>7}{'Recall':>8}{'FB':>6}{'Decomp':>8}"
    )
    print(f"{'='*110}")
    for record in records:
        question = record["question"][:35]
        print(
            f"{record['category']:<15}{question:<36}{record['faithfulness']:>7.2f}"
            f"{record['answer_relevancy']:>7.2f}{record['context_precision']:>7.2f}"
            f"{record['latency_seconds']:>8.2f}"
            f"{_format_optional(record['citation_correctness']):>7}"
            f"{_format_optional(record['recall_proxy']):>8}"
            f"{_format_bool(record['fallback_correct']):>6}"
            f"{_format_bool(record['decomposition_correct']):>8}"
        )


def _category_summaries(records: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["category"]].append(record)

    summaries = {}
    for category, items in sorted(grouped.items()):
        citations = [r["citation_correctness"] for r in items if r["citation_correctness"] is not None]
        recalls = [r["recall_proxy"] for r in items if r["recall_proxy"] is not None]
        summaries[category] = {
            "count": len(items),
            "faithfulness": round(_average([r["faithfulness"] for r in items]), 4),
            "answer_relevancy": round(_average([r["answer_relevancy"] for r in items]), 4),
            "context_precision": round(_average([r["context_precision"] for r in items]), 4),
            "latency_seconds": round(_average([r["latency_seconds"] for r in items]), 4),
            "citation_correctness": round(_average(citations), 4) if citations else None,
            "recall_proxy": round(_average(recalls), 4) if recalls else None,
            "fallback_accuracy": round(_average([1.0 if r["fallback_correct"] else 0.0 for r in items]), 4),
            "decomposition_correct": round(_average([1.0 if r["decomposition_correct"] else 0.0 for r in items]), 4),
        }
    return summaries


def _print_summary(records: list[dict], skipped: list[dict], generator: Generator, judge: Generator) -> None:
    if not records:
        logger.warning("No OK records available for summary")
        return

    _print_case_table(records)

    avg_faith = _average([r["faithfulness"] for r in records])
    avg_relev = _average([r["answer_relevancy"] for r in records])
    avg_prec = _average([r["context_precision"] for r in records])
    avg_all = _average([r["average"] for r in records])
    avg_latency = _average([r["latency_seconds"] for r in records])
    citations = [r["citation_correctness"] for r in records if r["citation_correctness"] is not None]
    recalls = [r["recall_proxy"] for r in records if r["recall_proxy"] is not None]
    fallback_accuracy = _average([1.0 if r["fallback_correct"] else 0.0 for r in records])

    print(f"{'='*100}")
    print("AVERAGE / SUCCESS CRITERIA CHECK:")
    print(f"  Faithfulness:          {avg_faith:.4f}  (target >=0.90)  {_pass_fail(avg_faith >= 0.90)}")
    print(f"  Answer Relevancy:      {avg_relev:.4f}")
    print(f"  Context Precision:     {avg_prec:.4f}")
    print(f"  Overall Judge Average: {avg_all:.4f}")
    print(f"  Avg Latency:           {avg_latency:.2f}s  (target <5s)  {_pass_fail(avg_latency < 5)}")
    if citations:
        avg_citation = _average(citations)
        print(f"  Citation Correctness:  {avg_citation:.4f}  (target >=0.90)  {_pass_fail(avg_citation >= 0.90)}")
    if recalls:
        avg_recall = _average(recalls)
        print(f"  Recall Proxy:          {avg_recall:.4f}  (target >=0.85)  {_pass_fail(avg_recall >= 0.85)}")
    print(f"  Fallback Accuracy:     {fallback_accuracy:.4f}")

    summaries = _category_summaries(records)
    print(f"\n{'='*110}")
    print("CATEGORY SUMMARY:")
    print(
        f"{'Category':<15}{'N':>4}{'Faith':>8}{'Relev':>8}{'Prec':>8}"
        f"{'Latency':>10}{'Cite':>8}{'Recall':>8}{'Fallback':>10}{'DecompOK':>10}"
    )
    print(f"{'-'*110}")
    for category, summary in summaries.items():
        print(
            f"{category:<15}{summary['count']:>4}{summary['faithfulness']:>8.2f}"
            f"{summary['answer_relevancy']:>8.2f}{summary['context_precision']:>8.2f}"
            f"{summary['latency_seconds']:>10.2f}"
            f"{_format_optional(summary['citation_correctness']):>8}"
            f"{_format_optional(summary['recall_proxy']):>8}"
            f"{summary['fallback_accuracy']:>10.2f}{summary['decomposition_correct']:>10.2f}"
        )

    if "enumeration" in summaries:
        print(
            "\nEnumeration decomposition correctness: "
            f"{summaries['enumeration']['decomposition_correct']:.4f}"
        )

    if skipped:
        logger.warning("Skipped cases: %d", len(skipped))
        for record in skipped:
            logger.warning("  - [%s] %s", record.get("status"), record["question"][:60])

    output = {
        "timestamp": datetime.now().isoformat(),
        "generator_model": generator.model,
        "judge_model": judge.model,
        "num_test_cases": len(records),
        "num_skipped": len(skipped),
        "averages": {
            "faithfulness": round(avg_faith, 4),
            "answer_relevancy": round(avg_relev, 4),
            "context_precision": round(avg_prec, 4),
            "overall": round(avg_all, 4),
            "latency_seconds": round(avg_latency, 4),
            "citation_correctness": round(_average(citations), 4) if citations else None,
            "recall_proxy": round(_average(recalls), 4) if recalls else None,
            "fallback_accuracy": round(fallback_accuracy, 4),
        },
        "category_summaries": summaries,
        "results": records,
        "skipped": skipped,
    }
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Results saved to: %s", OUTPUT_PATH)


def main() -> None:
    embedder = Embedder()
    generator = Generator(provider="groq")
    judge_generator = Generator(provider="gemini")
    evaluator = RAGEvaluator(judge_generator=judge_generator)

    done_cases = load_checkpoint()
    records = list(done_cases.values())
    skipped = []

    with VectorStore(path=settings.data_processed_dir / "qdrant") as store:
        all_chunks = load_embedded_chunks(settings.data_processed_dir)
        logger.info("Loaded %d chunks for BM25 index", len(all_chunks))
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=all_chunks)
        pipeline = RAGPipeline(retriever=retriever, generator=generator)
        decomposer = QueryDecomposer(pipeline=pipeline)

        for tc in TEST_SET:
            if tc.question in done_cases:
                logger.info("SKIP checkpoint OK: %s", tc.question[:60])
                continue

            logger.info("[%s] %s", tc.category, tc.question[:60])
            t0 = time.perf_counter()
            response, error = call_with_capped_retry(
                decomposer.run,
                question=tc.question,
                top_k=5,
                ticker=tc.ticker,
                section=tc.section,
            )

            if response is None:
                record = {
                    "question": tc.question,
                    "category": tc.category,
                    "status": "SKIPPED_QUOTA",
                    "error": error,
                    "timestamp": datetime.now().isoformat(),
                }
                append_checkpoint(record)
                skipped.append(record)
                logger.error("Skipped due to generation/decomposition error: %s", tc.question[:60])
                continue

            latency = time.perf_counter() - t0
            judge_scores, judge_error = call_with_capped_retry(
                evaluator.evaluate_one,
                question=tc.question,
                answer=response.answer,
                chunks=response.all_chunks,
                ground_truth=tc.ground_truth,
            )

            if judge_scores is None:
                record = {
                    "question": tc.question,
                    "category": tc.category,
                    "status": "JUDGE_SKIPPED_QUOTA",
                    "error": judge_error,
                    "answer": response.answer,
                    "latency_seconds": round(latency, 3),
                    "was_decomposed": response.was_decomposed,
                    "decomposition_expected": tc.expects_decomposition,
                    "decomposition_correct": response.was_decomposed == tc.expects_decomposition,
                    "sub_queries": _sub_queries(response),
                    "timestamp": datetime.now().isoformat(),
                }
                append_checkpoint(record)
                skipped.append(record)
                logger.error("Skipped judge due to quota/error: %s", tc.question[:60])
                continue

            record = _record_success(tc, response, judge_scores, latency)
            append_checkpoint(record)
            records.append(record)
            logger.info(
                "  Faith=%.2f Relev=%.2f Prec=%.2f | Latency=%.2fs | "
                "Citation=%s | Recall=%s | FallbackOK=%s | DecompOK=%s",
                record["faithfulness"],
                record["answer_relevancy"],
                record["context_precision"],
                record["latency_seconds"],
                _format_optional(record["citation_correctness"]),
                _format_optional(record["recall_proxy"]),
                record["fallback_correct"],
                record["decomposition_correct"],
            )
            time.sleep(1.5)

    _print_summary(records, skipped, generator, judge_generator)


if __name__ == "__main__":
    main()
