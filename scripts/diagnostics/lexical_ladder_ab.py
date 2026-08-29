"""Offline A/B gate for the field-aware lexical ladder.

Both arms use the same shaped query. The baseline runs the existing BM25 plus
semantic RRF, while the treatment adds the first non-empty lexical-ladder tier
before cross-encoder reranking. No provider or corpus mutation is allowed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from configs.offline_guard import offline_socket_guard
from configs.settings import settings
from scripts.diagnostics.query_shaper_ab import (
    DEFAULT_ARTIFACT,
    _all_terms_hit,
    _required_terms,
    _summarize_results,
)
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.lexical_ladder import (
    LEXICAL_LADDER_FINGERPRINT,
    lexical_ladder_candidates,
)
from src.retrieval.query_shaper import shape_retrieval_query
from src.retrieval.vector_store import VectorStore


def _scoped_chunks(
    retriever: HybridRetriever,
    ticker: str | None,
    section: str | None,
) -> list[dict]:
    return [
        chunk
        for chunk in retriever._all_chunks
        if (ticker is None or chunk["ticker"] == ticker)
        and (section is None or chunk["section"] == section)
    ]


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
                raise RuntimeError("Lexical-ladder A/B requires the trusted local index")
            chunks = load_retrieval_chunks(store, settings.data_processed_dir)
            retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)

            for case_payload in artifact["cases"]:
                required_terms = _required_terms(case_payload["question"])
                for query_entry in case_payload["queries"]:
                    plan = query_entry["query"]
                    shaped = shape_retrieval_query(plan["effective_query"])
                    has_hints = bool(
                        shaped.exact_phrases
                        or shaped.full_terms
                        or shaped.partial_terms
                        or shaped.fuzzy_terms
                    )
                    baseline = retriever.retrieve(
                        shaped.retrieval_query,
                        top_k=top_k,
                        ticker=plan["ticker"],
                        section=plan["section"],
                        candidate_pool=candidate_pool,
                        use_lexical_ladder=False,
                    )
                    treatment = retriever.retrieve(
                        shaped.retrieval_query,
                        top_k=top_k,
                        ticker=plan["ticker"],
                        section=plan["section"],
                        candidate_pool=candidate_pool,
                        use_lexical_ladder=True,
                    )
                    lexical = lexical_ladder_candidates(
                        _scoped_chunks(retriever, plan["ticker"], plan["section"]),
                        ticker=plan["ticker"],
                        section=plan["section"],
                        exact_phrases=shaped.exact_phrases,
                        full_terms=shaped.full_terms,
                        partial_terms=shaped.partial_terms,
                        fuzzy_terms=shaped.fuzzy_terms,
                        max_candidates=candidate_pool,
                    )
                    baseline_summary = _summarize_results(
                        baseline, plan["ticker"], required_terms
                    )
                    treatment_summary = _summarize_results(
                        treatment, plan["ticker"], required_terms
                    )
                    rows.append({
                        "question": case_payload["question"],
                        "ticker": plan["ticker"],
                        "section": plan["section"],
                        "retrieval_query": shaped.retrieval_query,
                        "has_hints": has_hints,
                        "lexical_tier": lexical[0].tier if lexical else None,
                        "lexical_chunk_ids": [item.chunk["chunk_id"] for item in lexical],
                        "baseline": baseline_summary,
                        "treatment": treatment_summary,
                        "required_terms_not_regressed": (
                            not _all_terms_hit(baseline_summary)
                            or _all_terms_hit(treatment_summary)
                        ),
                    })

    rows.sort(
        key=lambda row: (
            row["question"], row["retrieval_query"], row["ticker"] or ""
        )
    )
    hinted = [row for row in rows if row["has_hints"]]
    unhinted = [row for row in rows if not row["has_hints"]]
    report = {
        "schema_version": 1,
        "artifact_fingerprint": artifact["fingerprints"]["artifact"],
        "lexical_ladder_fingerprint": LEXICAL_LADDER_FINGERPRINT,
        "top_k": top_k,
        "candidate_pool": candidate_pool,
        "num_subqueries": len(rows),
        "num_hinted": len(hinted),
        "num_lexical_candidates": sum(len(row["lexical_chunk_ids"]) for row in hinted),
        "num_ticker_leakage": sum(
            row[arm]["ticker_leakage"]
            for row in rows
            for arm in ("baseline", "treatment")
        ),
        "num_required_term_regressions": sum(
            not row["required_terms_not_regressed"] for row in rows
        ),
        "all_unhinted_byte_stable": all(
            row["baseline"] == row["treatment"] for row in unhinted
        ),
        "all_hinted_have_candidates": all(row["lexical_chunk_ids"] for row in hinted),
        "cases": rows,
    }
    report["passed"] = (
        report["num_ticker_leakage"] == 0
        and report["num_required_term_regressions"] == 0
        and report["all_unhinted_byte_stable"]
        and report["all_hinted_have_candidates"]
    )
    return report


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
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
