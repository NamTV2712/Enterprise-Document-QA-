"""Auditable replay plans, raw facts, fidelity, and retrieval execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable, Literal, Protocol

from scripts.diagnostics.context_duplicate_metrics import (
    CaseDiagnostic,
    ChunkRecord,
    SimilarityMap,
    build_case_diagnostic,
)


@dataclass(frozen=True)
class ReplayQueryFacts:
    effective_query: str
    query_source: Literal[
        "original_question",
        "saved_subquery",
        "regenerated_rewrite",
        "original_proxy_missing_rewrite",
    ]
    ticker: str | None
    section: str | None
    retrieved_chunk_ids: tuple[str, ...]
    historical_num_chunks: int | None = None


@dataclass(frozen=True)
class ReplayQueryPlan:
    effective_query: str
    query_source: Literal[
        "original_question",
        "saved_subquery",
        "regenerated_rewrite",
        "original_proxy_missing_rewrite",
    ]
    ticker: str | None
    section: str | None
    historical_num_chunks: int | None = None


@dataclass(frozen=True)
class EvaluationReplayPlan:
    original_question: str
    category: str
    ticker: str | None
    section: str | None
    official_context_precision: float
    route: Literal["direct", "decomposed"]
    query_plans: tuple[ReplayQueryPlan, ...]
    evaluation_case_fingerprint: str | None


@dataclass(frozen=True)
class ReplayFacts:
    original_question: str
    route: Literal["direct", "decomposed"]
    corpus_source: Literal["local", "cloud"]
    top_k: int
    executed_queries: tuple[ReplayQueryFacts, ...]
    final_chunk_ids: tuple[str, ...]
    corpus_fingerprint: str | None = None
    retrieval_fingerprint: str | None = None
    missing_rewrite_policy: Literal["original_proxy", "regenerate"] | None = None


@dataclass(frozen=True)
class ReplayAssessment:
    query_fidelity: Literal["high", "low"]
    reasons: tuple[str, ...]
    historical_context_comparison: Literal["unavailable"] = "unavailable"


@dataclass(frozen=True)
class ReplayRecord:
    facts: ReplayFacts
    assessment: ReplayAssessment


@dataclass(frozen=True)
class RetrievalReplayExecution:
    record: ReplayRecord
    chunks: tuple[dict[str, Any], ...]


class RetrieverProtocol(Protocol):
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        ticker: str | None = None,
        section: str | None = None,
    ) -> list[Any]: ...


def _validate_unique_chunk_ids(
    chunk_ids: tuple[str, ...],
    *,
    field_name: str,
) -> None:
    if any(not chunk_id for chunk_id in chunk_ids):
        raise ValueError(f"{field_name} contains an empty chunk ID")
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError(f"{field_name} contains duplicate chunk IDs")


def _assess_replay_query_fidelity(
    executed_queries: tuple[ReplayQueryFacts, ...],
) -> ReplayAssessment:
    query_sources = {query.query_source for query in executed_queries}
    reasons = []
    if "original_question" in query_sources:
        reasons.append("exact_original_query")
    if "saved_subquery" in query_sources:
        reasons.append("saved_subqueries_reused")
    if "regenerated_rewrite" in query_sources:
        reasons.append("regenerated_rewrite_not_historical")
    if "original_proxy_missing_rewrite" in query_sources:
        reasons.append("historical_effective_query_unavailable")

    low_fidelity_sources = {
        "regenerated_rewrite",
        "original_proxy_missing_rewrite",
    }
    return ReplayAssessment(
        query_fidelity=(
            "low"
            if query_sources & low_fidelity_sources
            else "high"
        ),
        reasons=tuple(reasons),
    )


def _validate_replay_header(
    *,
    original_question: str,
    route: str,
    corpus_source: str,
    top_k: int,
) -> None:
    if not original_question.strip():
        raise ValueError("original_question must not be empty")
    if route not in {"direct", "decomposed"}:
        raise ValueError(f"Unsupported replay route: {route}")
    if corpus_source not in {"local", "cloud"}:
        raise ValueError(f"Unsupported corpus source: {corpus_source}")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")


def _validate_replay_queries(
    *,
    original_question: str,
    route: str,
    queries: tuple[ReplayQueryFacts | ReplayQueryPlan, ...],
    query_label: str,
) -> None:
    if not queries:
        raise ValueError(f"Replay must contain at least one {query_label}")
    if route == "direct" and len(queries) != 1:
        raise ValueError(f"Direct replay must contain exactly one {query_label}")

    allowed_sources = (
        {
            "original_question",
            "regenerated_rewrite",
            "original_proxy_missing_rewrite",
        }
        if route == "direct"
        else {"saved_subquery"}
    )
    for index, query in enumerate(queries):
        if not query.effective_query.strip():
            raise ValueError(f"{query_label}[{index}] has an empty effective query")
        if query.query_source not in allowed_sources:
            raise ValueError(
                f"Query source {query.query_source!r} is invalid for route {route!r}"
            )
        if (
            query.query_source == "original_question"
            and query.effective_query != original_question
        ):
            raise ValueError(
                "original_question source must preserve the original query exactly"
            )


def build_replay_record(
    *,
    original_question: str,
    route: Literal["direct", "decomposed"],
    corpus_source: Literal["local", "cloud"],
    top_k: int,
    executed_queries: tuple[ReplayQueryFacts, ...],
    final_chunk_ids: tuple[str, ...],
    corpus_fingerprint: str | None = None,
    retrieval_fingerprint: str | None = None,
    missing_rewrite_policy: Literal["original_proxy", "regenerate"] | None = None,
) -> ReplayRecord:
    """Validate replay facts and assess query fidelity without changing facts."""
    _validate_replay_header(
        original_question=original_question,
        route=route,
        corpus_source=corpus_source,
        top_k=top_k,
    )
    _validate_replay_queries(
        original_question=original_question,
        route=route,
        queries=executed_queries,
        query_label="executed query",
    )
    for index, query in enumerate(executed_queries):
        _validate_unique_chunk_ids(
            query.retrieved_chunk_ids,
            field_name=f"executed_queries[{index}].retrieved_chunk_ids",
        )

    _validate_unique_chunk_ids(final_chunk_ids, field_name="final_chunk_ids")
    returned_chunk_ids = {
        chunk_id
        for query in executed_queries
        for chunk_id in query.retrieved_chunk_ids
    }
    final_chunk_id_set = set(final_chunk_ids)
    unknown_final_ids = final_chunk_id_set - returned_chunk_ids
    if unknown_final_ids:
        raise ValueError(
            "Final chunk IDs were not returned by an executed query: "
            f"{sorted(unknown_final_ids)}"
        )
    omitted_returned_ids = returned_chunk_ids - final_chunk_id_set
    if omitted_returned_ids:
        raise ValueError(
            "Final chunk IDs omit chunks returned by executed queries: "
            f"{sorted(omitted_returned_ids)}"
        )

    facts = ReplayFacts(
        original_question=original_question,
        route=route,
        corpus_source=corpus_source,
        top_k=top_k,
        executed_queries=executed_queries,
        final_chunk_ids=final_chunk_ids,
        corpus_fingerprint=corpus_fingerprint,
        retrieval_fingerprint=retrieval_fingerprint,
        missing_rewrite_policy=missing_rewrite_policy,
    )
    return ReplayRecord(
        facts=facts,
        assessment=_assess_replay_query_fidelity(executed_queries),
    )


def build_case_diagnostic_from_replay(
    *,
    replay_record: ReplayRecord,
    category: str,
    official_context_precision: float,
    chunks: list[ChunkRecord],
    ticker: str | None = None,
    section: str | None = None,
    semantic_similarities: SimilarityMap | None = None,
    semantic_thresholds: tuple[float, ...] = (0.90, 0.95, 0.98),
) -> CaseDiagnostic:
    """Build derived metrics only when chunks match the immutable replay facts."""
    chunk_ids = tuple(str(chunk.get("chunk_id", "")) for chunk in chunks)
    if chunk_ids != replay_record.facts.final_chunk_ids:
        raise ValueError(
            "Diagnostic chunks must preserve replay final_chunk_ids and order"
        )
    return build_case_diagnostic(
        question=replay_record.facts.original_question,
        category=category,
        ticker=ticker,
        section=section,
        official_context_precision=official_context_precision,
        replay_fidelity=replay_record.assessment.query_fidelity,
        chunks=chunks,
        semantic_similarities=semantic_similarities,
        semantic_thresholds=semantic_thresholds,
    )


def _retrieved_chunk_id(result: Any) -> str:
    chunk_id = (
        result.get("chunk_id")
        if isinstance(result, Mapping)
        else getattr(result, "chunk_id", None)
    )
    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("Retriever returned a result without a valid chunk_id")
    return chunk_id


def execute_retrieval_replay(
    *,
    retriever: RetrieverProtocol,
    original_question: str,
    route: Literal["direct", "decomposed"],
    corpus_source: Literal["local", "cloud"],
    top_k: int,
    query_plans: tuple[ReplayQueryPlan, ...],
    chunks_by_id: Mapping[str, ChunkRecord],
    corpus_fingerprint: str | None = None,
    retrieval_fingerprint: str | None = None,
    missing_rewrite_policy: Literal["original_proxy", "regenerate"] | None = None,
) -> RetrievalReplayExecution:
    """Replay retrieval and hydrate ranked IDs from the active corpus catalog."""
    _validate_replay_header(
        original_question=original_question,
        route=route,
        corpus_source=corpus_source,
        top_k=top_k,
    )
    _validate_replay_queries(
        original_question=original_question,
        route=route,
        queries=query_plans,
        query_label="query plan",
    )

    executed_queries = []
    final_chunk_ids_by_first_occurrence: dict[str, None] = {}
    for plan in query_plans:
        results = retriever.retrieve(
            query=plan.effective_query,
            top_k=top_k,
            ticker=plan.ticker,
            section=plan.section,
        )
        retrieved_chunk_ids = tuple(_retrieved_chunk_id(result) for result in results)
        for chunk_id in retrieved_chunk_ids:
            final_chunk_ids_by_first_occurrence.setdefault(chunk_id, None)
        executed_queries.append(
            ReplayQueryFacts(
                effective_query=plan.effective_query,
                query_source=plan.query_source,
                ticker=plan.ticker,
                section=plan.section,
                retrieved_chunk_ids=retrieved_chunk_ids,
                historical_num_chunks=plan.historical_num_chunks,
            )
        )

    final_chunk_ids = tuple(final_chunk_ids_by_first_occurrence)
    record = build_replay_record(
        original_question=original_question,
        route=route,
        corpus_source=corpus_source,
        top_k=top_k,
        executed_queries=tuple(executed_queries),
        final_chunk_ids=final_chunk_ids,
        corpus_fingerprint=corpus_fingerprint,
        retrieval_fingerprint=retrieval_fingerprint,
        missing_rewrite_policy=missing_rewrite_policy,
    )

    canonical_chunks = []
    for chunk_id in final_chunk_ids:
        catalog_chunk = chunks_by_id.get(chunk_id)
        if catalog_chunk is None:
            raise ValueError(
                f"Retrieved chunk ID {chunk_id!r} is missing from the corpus catalog"
            )
        canonical_chunk = dict(catalog_chunk)
        if canonical_chunk.get("chunk_id") != chunk_id:
            raise ValueError(
                f"Corpus catalog payload for {chunk_id!r} has a mismatched chunk_id"
            )
        canonical_chunk.pop("embedding", None)
        canonical_chunks.append(canonical_chunk)

    return RetrievalReplayExecution(
        record=record,
        chunks=tuple(canonical_chunks),
    )


def _optional_artifact_filter(
    record: Mapping[str, Any],
    field_name: str,
) -> str | None:
    value = record.get(field_name)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"Artifact field {field_name!r} must be a string or null")
    return value


def build_replay_plan_from_evaluation_record(
    record: Mapping[str, Any],
    *,
    requires_rewrite: Callable[[str], bool],
    missing_rewrite_strategy: Literal["original_proxy", "regenerate"],
    regenerate_query: Callable[[str], str] | None = None,
) -> EvaluationReplayPlan:
    """Convert one historical evaluation record into an explicit replay plan."""
    if missing_rewrite_strategy not in {"original_proxy", "regenerate"}:
        raise ValueError(
            f"Unsupported missing rewrite strategy: {missing_rewrite_strategy}"
        )
    if record.get("status") != "OK":
        raise ValueError("Only successful evaluation records can be replayed")

    question = record.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Evaluation record must contain a non-empty question")
    category = record.get("category")
    if not isinstance(category, str) or not category:
        raise ValueError("Evaluation record must contain a category")
    ticker = _optional_artifact_filter(record, "ticker")
    section = _optional_artifact_filter(record, "section")

    raw_precision = record.get("context_precision")
    if isinstance(raw_precision, bool) or not isinstance(raw_precision, (int, float)):
        raise ValueError("Evaluation record must contain numeric context_precision")
    precision = float(raw_precision)
    if not isfinite(precision) or not 0.0 <= precision <= 1.0:
        raise ValueError("Evaluation context_precision must be between 0 and 1")

    was_decomposed = record.get("was_decomposed")
    if not isinstance(was_decomposed, bool):
        raise ValueError("Evaluation record must contain boolean was_decomposed")
    raw_sub_queries = record.get("sub_queries")
    if not isinstance(raw_sub_queries, list):
        raise ValueError("Evaluation record sub_queries must be a list")

    if was_decomposed:
        if not raw_sub_queries:
            raise ValueError("Decomposed evaluation record has no saved subqueries")
        query_plans = []
        for index, raw_sub_query in enumerate(raw_sub_queries):
            if not isinstance(raw_sub_query, Mapping):
                raise ValueError(f"sub_queries[{index}] must be an object")
            query = raw_sub_query.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"sub_queries[{index}] has an empty query")
            historical_num_chunks = raw_sub_query.get("num_chunks")
            if (
                isinstance(historical_num_chunks, bool)
                or not isinstance(historical_num_chunks, int)
                or historical_num_chunks < 0
            ):
                raise ValueError(
                    f"sub_queries[{index}].num_chunks must be a non-negative integer"
                )
            query_plans.append(
                ReplayQueryPlan(
                    effective_query=query,
                    query_source="saved_subquery",
                    ticker=_optional_artifact_filter(raw_sub_query, "ticker"),
                    section=_optional_artifact_filter(raw_sub_query, "section"),
                    historical_num_chunks=historical_num_chunks,
                )
            )
        route: Literal["direct", "decomposed"] = "decomposed"
    else:
        if raw_sub_queries:
            raise ValueError("Direct evaluation record unexpectedly has saved subqueries")
        if requires_rewrite(question):
            if missing_rewrite_strategy == "regenerate":
                if regenerate_query is None:
                    raise ValueError(
                        "regenerate strategy requires a regenerate_query callback"
                    )
                effective_query = regenerate_query(question)
                if not isinstance(effective_query, str) or not effective_query.strip():
                    raise ValueError("Regenerated query must be a non-empty string")
                query_source = "regenerated_rewrite"
            else:
                effective_query = question
                query_source = "original_proxy_missing_rewrite"
        else:
            effective_query = question
            query_source = "original_question"
        query_plans = [
            ReplayQueryPlan(
                effective_query=effective_query,
                query_source=query_source,
                ticker=ticker,
                section=section,
            )
        ]
        route = "direct"

    fingerprint = record.get("fingerprint")
    if fingerprint is not None and not isinstance(fingerprint, str):
        raise ValueError("Evaluation fingerprint must be a string or null")
    return EvaluationReplayPlan(
        original_question=question,
        category=category,
        ticker=ticker,
        section=section,
        official_context_precision=precision,
        route=route,
        query_plans=tuple(query_plans),
        evaluation_case_fingerprint=fingerprint,
    )
