"""
Script: run_evaluation.py
Run the entire test set, print the results table, and save it to JSON.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from configs.settings import settings
from src.evaluation.evaluator import RAGEvaluator
from src.evaluation.test_set import TEST_SET
from src.generation.generator import Generator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever, load_embedded_chunks
from src.retrieval.vector_store import VectorStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    # --- Initialize pipeline ---
    embedder = Embedder()
    generator = Generator(provider="groq")

    # Judge dùng cùng model — trong production nên dùng model khác để tránh bias
    judge_generator = Generator(provider="groq")
    evaluator = RAGEvaluator(judge_generator=judge_generator)

    results = []
    with VectorStore(path=settings.data_processed_dir / "qdrant") as store:
        all_chunks = load_embedded_chunks(settings.data_processed_dir)
        logger.info("Loaded %d chunks for BM25 index", len(all_chunks))
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=all_chunks)
        pipeline = RAGPipeline(retriever=retriever, generator=generator)

        for tc in TEST_SET:
            logger.info("Evaluating: %s", tc.question[:60])
            response = pipeline.query(
                question=tc.question,
                top_k=5,
                ticker=tc.ticker,
                section=tc.section,
            )
            result = evaluator.evaluate_one(
                question=tc.question,
                answer=response.answer,
                chunks=response.retrieved_chunks,
                ground_truth=tc.ground_truth,
            )
            results.append(result)
            logger.info(
                "  Faithfulness=%.2f | Relevancy=%.2f | Precision=%.2f | Avg=%.2f",
                result.faithfulness, result.answer_relevancy,
                result.context_precision, result.average_score,
            )
            time.sleep(2)

    # --- Print summary table ---
    print(f"\n{'='*70}")
    print(f"{'Question':<45} {'Faith':>6} {'Relev':>6} {'Prec':>6} {'Avg':>6}")
    print(f"{'='*70}")
    for r in results:
        q = r.question[:44]
        print(f"{q:<45} {r.faithfulness:>6.2f} {r.answer_relevancy:>6.2f} "
              f"{r.context_precision:>6.2f} {r.average_score:>6.2f}")

    avg_faith = sum(r.faithfulness for r in results) / len(results)
    avg_relev = sum(r.answer_relevancy for r in results) / len(results)
    avg_prec = sum(r.context_precision for r in results) / len(results)
    avg_all = sum(r.average_score for r in results) / len(results)
    print(f"{'='*70}")
    print(f"{'AVERAGE':<45} {avg_faith:>6.2f} {avg_relev:>6.2f} {avg_prec:>6.2f} {avg_all:>6.2f}")

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
        },
        "results": [
            {
                "question": r.question,
                "faithfulness": r.faithfulness,
                "answer_relevancy": r.answer_relevancy,
                "context_precision": r.context_precision,
                "average": r.average_score,
                "reasons": {
                    "faithfulness": r.faithfulness_reason,
                    "relevancy": r.relevancy_reason,
                    "precision": r.precision_reason,
                },
            }
            for r in results
        ],
    }
    out_path = Path("data/evaluation_results.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    logger.info("Results saved to: %s", out_path)


if __name__ == "__main__":
    main()
