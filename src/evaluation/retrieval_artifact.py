"""Deterministic retrieval-artifact construction for evaluation Phase 1.

Phase 1 executes the frozen retrieval plans against the trusted local
index and writes a canonical JSON artifact containing ordered chunk
evidence plus every fingerprint needed by Phase 2 to bind itself to the
exact retrieval conditions. The artifact contains no timestamps or
latencies: two executions on the same environment must serialize to
byte-identical output.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from configs.settings import settings
from src.evaluation.retrieval_plan import (
    PLAN_SCHEMA_VERSION,
    RetrievalPlan,
    compute_plan_fingerprint,
    plans_to_payload,
)
from src.evaluation.test_set import TestCase
from src.retrieval.index_manifest import compute_corpus_fingerprint

ARTIFACT_SCHEMA_VERSION = 1
SCORE_PRECISION = 6


class SupportsRetrieve(Protocol):
    """Minimal retriever surface used by Phase 1 (no LLM anywhere)."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
    ) -> list[Any]:
        ...


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _chunk_to_record(chunk: Any) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "ticker": chunk.ticker,
        "section": chunk.section,
        "filing_date": chunk.filing_date,
        "score": round(float(chunk.score), SCORE_PRECISION),
        "citation": chunk.citation,
        "text": chunk.text,
    }


@dataclass
class QueryRetrievalResult:
    query: dict[str, Any]
    chunks: list[dict[str, Any]]


@dataclass
class CaseRetrievalResult:
    question: str
    category: str
    route: str
    queries: list[QueryRetrievalResult]

    @property
    def final_chunk_ids(self) -> list[str]:
        """First-occurrence order across branches, matching decomposer dedupe."""
        seen: list[str] = []
        for query_result in self.queries:
            for chunk in query_result.chunks:
                if chunk["chunk_id"] not in seen:
                    seen.append(chunk["chunk_id"])
        return seen


def execute_case_retrieval(
    retriever: SupportsRetrieve,
    case: TestCase,
    plan: RetrievalPlan,
    top_k: int = 5,
) -> CaseRetrievalResult:
    """Run one frozen plan through pure retrieval; never calls an LLM."""
    query_results: list[QueryRetrievalResult] = []
    for plan_query in plan.queries:
        chunks = retriever.retrieve(
            query=plan_query.effective_query,
            top_k=top_k,
            ticker=plan_query.ticker,
            section=plan_query.section,
        )
        query_results.append(
            QueryRetrievalResult(
                query={
                    "effective_query": plan_query.effective_query,
                    "ticker": plan_query.ticker,
                    "section": plan_query.section,
                    "query_source": plan_query.query_source,
                },
                chunks=[_chunk_to_record(chunk) for chunk in chunks],
            )
        )
    return CaseRetrievalResult(
        question=case.question,
        category=case.category,
        route=plan.route,
        queries=query_results,
    )


def _embedding_fingerprint() -> str:
    payload = {
        "model_id": settings.embedding_model_id,
        "revision": settings.embedding_model_revision,
        "document_prefix": True,
    }
    return _sha256_text(json.dumps(payload, sort_keys=True))


def _reranker_fingerprint() -> str:
    from src.retrieval.hybrid_retriever import (
        CROSS_ENCODER_BATCH_SIZE,
        CROSS_ENCODER_MODEL,
    )

    payload = {
        "model": CROSS_ENCODER_MODEL,
        "batch_size": CROSS_ENCODER_BATCH_SIZE,
    }
    return _sha256_text(json.dumps(payload, sort_keys=True))


def compute_index_manifest_fingerprint(manifest_path: Path | None) -> str | None:
    """SHA-256 of the trusted index manifest file, when present."""
    if manifest_path is None:
        manifest_path = settings.qdrant_index_manifest_path
    if not manifest_path.exists():
        return None
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def build_retrieval_artifact(
    test_cases: list[TestCase],
    plans: list[RetrievalPlan],
    results: list[CaseRetrievalResult],
    all_chunks: list[dict],
    top_k: int,
) -> dict[str, Any]:
    """Assemble the canonical Phase 1 artifact (no timestamps inside)."""
    plan_by_question = {plan.question: plan for plan in plans}
    case_by_question = {case.question: case for case in test_cases}

    case_payloads: list[dict[str, Any]] = []
    for result in results:
        case = case_by_question[result.question]
        case_payloads.append(
            {
                "question": result.question,
                "category": result.category,
                "route": result.route,
                "expects_fallback": case.expects_fallback,
                "required_keywords": case.required_keywords,
                "ground_truth": case.ground_truth,
                "queries": [
                    {
                        "query": qr.query,
                        "chunks": qr.chunks,
                    }
                    for qr in result.queries
                ],
                "final_chunk_ids": result.final_chunk_ids,
            }
        )

    fingerprints: dict[str, Any] = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "plan_schema_version": PLAN_SCHEMA_VERSION,
        "test_set": _sha256_text(
            json.dumps(
                sorted(case.question for case in test_cases),
                separators=(",", ":"),
                ensure_ascii=False,
            )
        ),
        "plan": compute_plan_fingerprint(plans),
        "corpus": compute_corpus_fingerprint(all_chunks),
        "index_manifest": compute_index_manifest_fingerprint(None),
        "embedding": _embedding_fingerprint(),
        "reranker": _reranker_fingerprint(),
        "retrieval_config": _sha256_text(
            json.dumps(
                {"top_k": top_k, "route_policy": "frozen_official_v2"},
                sort_keys=True,
            )
        ),
    }

    artifact_core = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "plans": plans_to_payload(plans),
        "cases": case_payloads,
        "fingerprints": fingerprints,
    }
    artifact_core["fingerprints"]["artifact"] = _sha256_text(
        canonical_json(artifact_core).decode("utf-8")
    )
    return artifact_core


def canonical_json(payload: Any) -> bytes:
    """Byte-stable serialization used for hashing and writing artifacts."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def write_artifact(artifact: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(artifact))
