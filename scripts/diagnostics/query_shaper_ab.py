"""Offline A/B audit of deterministic query shaping over frozen Phase 1 plans.

The script replays every frozen sub-query against the trusted local index. It
never calls a provider or mutates corpus/index artifacts. Unchanged queries are
retrieved once and reused for both arms, while changed queries are executed in
both forms so the report isolates the effect of query shaping.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from configs.offline_guard import offline_socket_guard
from configs.settings import settings
from scripts.diagnostics.audit_decomposed_plans import EXPECTED_FACT_OVERRIDES
from src.evaluation.test_set import TEST_SET
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_shaper import shape_retrieval_query
from src.retrieval.vector_store import VectorStore


DEFAULT_ARTIFACT = Path("data/eval_artifacts/phase1_priority2.json")


def _compact(text: str) -> str:
    return "".join(text.split()).casefold()


def _required_terms(question: str) -> tuple[str, ...]:
    case = next(case for case in TEST_SET if case.question == question)
    return tuple(dict.fromkeys([
        *case.required_keywords,
        *EXPECTED_FACT_OVERRIDES.get(question, ()),
    ]))


def _summarize_results(
    results: list[Any], ticker: str | None, required_terms: tuple[str, ...]
) -> dict[str, Any]:
    evidence = " ".join(chunk.text for chunk in results)
    compact_evidence = _compact(evidence)
    return {
        "chunk_ids": [chunk.chunk_id for chunk in results],
        "tickers": [chunk.ticker for chunk in results],
        "ticker_leakage": bool(ticker and any(chunk.ticker != ticker for chunk in results)),
        "required_term_hits": {
            term: _compact(term) in compact_evidence for term in required_terms
        },
    }


def _all_terms_hit(summary: dict[str, Any]) -> bool:
    return all(summary["required_term_hits"].values())


def run(artifact_path: Path, top_k: int, candidate_pool: int) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

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
            if store.mode != "local":
                raise RuntimeError("Query-shaper A/B requires the trusted local index")
            chunks = load_retrieval_chunks(store, settings.data_processed_dir)
            retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)
            for case_payload in artifact["cases"]:
                required_terms = _required_terms(case_payload["question"])
                for query_entry in case_payload["queries"]:
                    plan = query_entry["query"]
                    original_query = plan["effective_query"]
                    shaped = shape_retrieval_query(original_query)
                    original_results = retriever.retrieve(
                        original_query, top_k=top_k, ticker=plan["ticker"],
                        section=plan["section"], candidate_pool=candidate_pool,
                    )
                    if shaped.retrieval_query == original_query:
                        shaped_results = original_results
                        shaped_reexecuted = False
                    else:
                        shaped_results = retriever.retrieve(
                            shaped.retrieval_query, top_k=top_k, ticker=plan["ticker"],
                            section=plan["section"], candidate_pool=candidate_pool,
                        )
                        shaped_reexecuted = True
                    original_summary = _summarize_results(
                        original_results, plan["ticker"], required_terms
                    )
                    shaped_summary = _summarize_results(
                        shaped_results, plan["ticker"], required_terms
                    )
                    rows.append({
                        "question": case_payload["question"],
                        "ticker": plan["ticker"],
                        "section": plan["section"],
                        "original_query": original_query,
                        "shaped_query": shaped.retrieval_query,
                        "changed": shaped_reexecuted,
                        "exact_phrases": shaped.exact_phrases,
                        "full_terms": shaped.full_terms,
                        "original": original_summary,
                        "shaped": shaped_summary,
                        "required_terms_not_regressed": (
                            not _all_terms_hit(original_summary)
                            or _all_terms_hit(shaped_summary)
                        ),
                    })

    rows.sort(key=lambda row: (row["question"], row["original_query"], row["ticker"] or ""))
    changed = [row for row in rows if row["changed"]]
    return {
        "schema_version": 1,
        "artifact_fingerprint": artifact["fingerprints"]["artifact"],
        "top_k": top_k,
        "candidate_pool": candidate_pool,
        "num_subqueries": len(rows),
        "num_shaped": len(changed),
        "num_ticker_leakage": sum(
            row[arm]["ticker_leakage"] for row in rows for arm in ("original", "shaped")
        ),
        "num_required_term_regressions": sum(
            not row["required_terms_not_regressed"] for row in changed
        ),
        "all_unchanged_byte_stable": all(
            row["original_query"] == row["shaped_query"]
            and row["original"] == row["shaped"]
            for row in rows if not row["changed"]
        ),
        "all_changed_terms_not_regressed": all(
            row["required_terms_not_regressed"] for row in changed
        ),
        "cases": rows,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-pool", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.artifact, args.top_k, args.candidate_pool)
    report["passed"] = (
        report["num_ticker_leakage"] == 0
        and report["num_required_term_regressions"] == 0
        and report["all_unchanged_byte_stable"]
        and report["all_changed_terms_not_regressed"]
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
