"""Pure orchestration for context-duplicate diagnostic runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Literal

from scripts.diagnostics.context_duplicate_metrics import (
    CaseDiagnostic,
    GroupDiagnostic,
    MetricAssociationDiagnostic,
    SimilarityMap,
    aggregate_case_diagnostics,
    analyze_metric_association,
    classify_correlation_cohort,
)
from scripts.diagnostics.replay_contract import (
    EvaluationReplayPlan,
    ReplayRecord,
    RetrieverProtocol,
    build_case_diagnostic_from_replay,
    build_replay_plan_from_evaluation_record,
    execute_retrieval_replay,
)


@dataclass(frozen=True)
class DiagnosticRunMetadata:
    corpus_source: Literal["local", "cloud"]
    corpus_fingerprint: str | None
    retrieval_fingerprint: str | None
    missing_rewrite_policy: Literal["original_proxy", "regenerate"]
    top_k: int
    semantic_thresholds: tuple[float, ...]


@dataclass(frozen=True)
class ReplayedCaseDiagnostic:
    evaluation_plan: EvaluationReplayPlan
    replay_record: ReplayRecord
    diagnostic: CaseDiagnostic


@dataclass(frozen=True)
class ReplayFailure:
    question: str
    category: str
    stage: str
    error_type: str
    message: str


@dataclass(frozen=True)
class ContextDuplicateDiagnosticReport:
    metadata: DiagnosticRunMetadata
    planned_cases: int
    planned_primary_eligible_cases: int
    successful_replays: int
    primary_eligible_cases: int
    cases: tuple[ReplayedCaseDiagnostic, ...]
    failures: tuple[ReplayFailure, ...]
    associations: tuple[MetricAssociationDiagnostic, ...]
    group_diagnostics: dict[str, tuple[GroupDiagnostic, ...]]

def _plan_has_high_query_fidelity(plan: EvaluationReplayPlan) -> bool:
    low_fidelity_sources = {
        "regenerated_rewrite",
        "original_proxy_missing_rewrite",
    }
    return not any(
        query.query_source in low_fidelity_sources
        for query in plan.query_plans
    )


def _metric_associations(
    diagnostics: list[CaseDiagnostic],
    semantic_thresholds: tuple[float, ...],
) -> tuple[MetricAssociationDiagnostic, ...]:
    metric_getters: list[tuple[str, Callable[[CaseDiagnostic], float]]] = [
        (
            "exact_duplicate_pair_rate",
            lambda case: case.context_metrics.exact_duplicate_pair_rate,
        ),
        (
            "adjacent_pair_rate",
            lambda case: case.context_metrics.adjacent_pair_rate,
        ),
        (
            "weighted_adjacent_containment",
            lambda case: case.context_metrics.weighted_adjacent_containment,
        ),
        (
            "pairwise_overlap_mass_rate",
            lambda case: case.context_metrics.pairwise_overlap_mass_rate,
        ),
    ]
    for threshold in semantic_thresholds:
        metric_getters.append(
            (
                f"semantic_only_pair_rate_at_{threshold:.2f}",
                lambda case, threshold=threshold: (
                    case.context_metrics.semantic_only_pair_rates_by_threshold[
                        threshold
                    ]
                ),
            )
        )
    return tuple(
        analyze_metric_association(
            diagnostics,
            metric_name=metric_name,
            metric_getter=metric_getter,
        )
        for metric_name, metric_getter in metric_getters
    )


def run_context_duplicate_diagnostic(
    *,
    records: list[Mapping[str, Any]],
    retriever: RetrieverProtocol,
    chunks: list[ChunkRecord],
    corpus_source: Literal["local", "cloud"],
    top_k: int,
    requires_rewrite: Callable[[str], bool],
    missing_rewrite_policy: Literal["original_proxy", "regenerate"],
    semantic_similarity_provider: Callable[
        [tuple[dict[str, Any], ...]],
        SimilarityMap,
    ],
    semantic_thresholds: tuple[float, ...] = (0.90, 0.95, 0.98),
    corpus_fingerprint: str | None = None,
    retrieval_fingerprint: str | None = None,
    regenerate_query: Callable[[str], str] | None = None,
) -> ContextDuplicateDiagnosticReport:
    """Orchestrate auditable current-runtime replay for historical eval cases."""
    thresholds = tuple(sorted(set(semantic_thresholds)))
    plans = [
        build_replay_plan_from_evaluation_record(
            record,
            requires_rewrite=requires_rewrite,
            missing_rewrite_strategy=missing_rewrite_policy,
            regenerate_query=regenerate_query,
        )
        for record in records
    ]
    planned_primary_eligible_cases = sum(
        plan.category != "out_of_corpus" and _plan_has_high_query_fidelity(plan)
        for plan in plans
    )

    chunk_ids = [str(chunk.get("chunk_id", "")) for chunk in chunks]
    if any(not chunk_id for chunk_id in chunk_ids):
        raise ValueError("Corpus catalog contains a chunk without chunk_id")
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Corpus catalog contains duplicate chunk IDs")
    chunks_by_id = dict(zip(chunk_ids, chunks, strict=True))

    replayed_cases = []
    failures = []
    for plan in plans:
        stage = "retrieval_replay"
        try:
            execution = execute_retrieval_replay(
                retriever=retriever,
                original_question=plan.original_question,
                route=plan.route,
                corpus_source=corpus_source,
                top_k=top_k,
                query_plans=plan.query_plans,
                chunks_by_id=chunks_by_id,
                corpus_fingerprint=corpus_fingerprint,
                retrieval_fingerprint=retrieval_fingerprint,
                missing_rewrite_policy=missing_rewrite_policy,
            )
            stage = "semantic_similarity"
            semantic_similarities = semantic_similarity_provider(execution.chunks)
            stage = "case_metrics"
            diagnostic = build_case_diagnostic_from_replay(
                replay_record=execution.record,
                category=plan.category,
                ticker=plan.ticker,
                section=plan.section,
                official_context_precision=plan.official_context_precision,
                chunks=list(execution.chunks),
                semantic_similarities=semantic_similarities,
                semantic_thresholds=thresholds,
            )
        except Exception as error:
            failures.append(
                ReplayFailure(
                    question=plan.original_question,
                    category=plan.category,
                    stage=stage,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )
            continue
        replayed_cases.append(
            ReplayedCaseDiagnostic(
                evaluation_plan=plan,
                replay_record=execution.record,
                diagnostic=diagnostic,
            )
        )

    diagnostics = [case.diagnostic for case in replayed_cases]
    primary_eligible_cases = sum(
        classify_correlation_cohort(diagnostic).eligible
        for diagnostic in diagnostics
    )
    group_diagnostics = {
        dimension: aggregate_case_diagnostics(
            diagnostics,
            group_by=dimension,
        )
        for dimension in ("category", "ticker", "section")
    }
    return ContextDuplicateDiagnosticReport(
        metadata=DiagnosticRunMetadata(
            corpus_source=corpus_source,
            corpus_fingerprint=corpus_fingerprint,
            retrieval_fingerprint=retrieval_fingerprint,
            missing_rewrite_policy=missing_rewrite_policy,
            top_k=top_k,
            semantic_thresholds=thresholds,
        ),
        planned_cases=len(plans),
        planned_primary_eligible_cases=planned_primary_eligible_cases,
        successful_replays=len(replayed_cases),
        primary_eligible_cases=primary_eligible_cases,
        cases=tuple(replayed_cases),
        failures=tuple(failures),
        associations=_metric_associations(diagnostics, thresholds),
        group_diagnostics=group_diagnostics,
    )
