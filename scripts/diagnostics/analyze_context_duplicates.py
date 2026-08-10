"""Runtime composition entry point for context-duplicate diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Literal

from scripts.diagnostics.diagnostic_runner import (
    ContextDuplicateDiagnosticReport,
    run_context_duplicate_diagnostic,
)
from scripts.diagnostics.diagnostic_fingerprints import (
    DiagnosticRunIdentity,
    compute_corpus_fingerprint,
    compute_diagnostic_contract_fingerprint,
    compute_replay_plan_fingerprint,
    compute_retrieval_fingerprint,
)
from scripts.diagnostics.replay_contract import (
    RetrieverProtocol,
    build_replay_plan_from_evaluation_record,
)


@dataclass(frozen=True)
class ComposedDiagnosticRun:
    identity: DiagnosticRunIdentity
    report: ContextDuplicateDiagnosticReport


def _manifest_mapping(
    manifest: Mapping[str, Any],
    field_name: str,
) -> Mapping[str, Any]:
    value = manifest.get(field_name)
    if not isinstance(value, Mapping):
        raise ValueError(f"Retrieval manifest field {field_name!r} must be an object")
    return value


def _validate_retrieval_manifest_coherence(
    manifest: Mapping[str, Any],
    *,
    corpus_fingerprint: str,
    top_k: int,
) -> None:
    if manifest.get("top_k") != top_k:
        raise ValueError("Retrieval manifest top_k does not match diagnostic top_k")
    if manifest.get("query_rewrite_policy") != "original_proxy":
        raise ValueError(
            "Retrieval manifest query rewrite policy must be original_proxy"
        )

    embedding_model = _manifest_mapping(manifest, "embedding_model")
    qdrant = _manifest_mapping(manifest, "qdrant")
    index_manifest = _manifest_mapping(manifest, "index_manifest")
    if index_manifest.get("corpus_fingerprint") != corpus_fingerprint:
        raise ValueError(
            "Index manifest corpus fingerprint does not match the active corpus"
        )
    if index_manifest.get("embedding_model_revision") != embedding_model.get(
        "revision"
    ):
        raise ValueError(
            "Index manifest embedding revision does not match retrieval config"
        )
    if index_manifest.get("vector_dimension") != embedding_model.get("dimension"):
        raise ValueError(
            "Index manifest vector dimension does not match the embedding model"
        )
    if index_manifest.get("distance_metric") != qdrant.get("distance"):
        raise ValueError(
            "Index manifest distance metric does not match Qdrant configuration"
        )


def compose_diagnostic_run(
    *,
    artifact: Mapping[str, Any],
    retriever: RetrieverProtocol,
    chunks: list[Mapping[str, Any]],
    corpus_source: Literal["local", "cloud"],
    top_k: int,
    requires_rewrite: Callable[[str], bool],
    semantic_similarity_provider: Callable[
        [tuple[dict[str, Any], ...]],
        Mapping[tuple[str, str], float],
    ],
    semantic_thresholds: tuple[float, ...] = (0.90, 0.95, 0.98),
    retrieval_manifest: Mapping[str, Any] | None = None,
) -> ComposedDiagnosticRun:
    """Compose a deterministic original-proxy run from injected dependencies."""
    if artifact.get("num_skipped") != 0:
        raise ValueError("Official evaluation artifact contains skipped records")
    raw_records = artifact.get("results")
    if not isinstance(raw_records, list) or not all(
        isinstance(record, Mapping)
        for record in raw_records
    ):
        raise ValueError("Evaluation artifact results must be a list of records")
    expected_cases = artifact.get("num_test_cases")
    if expected_cases is not None and expected_cases != len(raw_records):
        raise ValueError("Evaluation artifact case count does not match results")

    rewrite_decisions: dict[str, bool] = {}

    def cached_requires_rewrite(question: str) -> bool:
        if question not in rewrite_decisions:
            rewrite_decisions[question] = bool(requires_rewrite(question))
        return rewrite_decisions[question]

    plans = [
        build_replay_plan_from_evaluation_record(
            record,
            requires_rewrite=cached_requires_rewrite,
            missing_rewrite_strategy="original_proxy",
        )
        for record in raw_records
    ]
    corpus_fingerprint = compute_corpus_fingerprint(chunks)
    if retrieval_manifest is None:
        retrieval_fingerprint = None
    else:
        _validate_retrieval_manifest_coherence(
            retrieval_manifest,
            corpus_fingerprint=corpus_fingerprint,
            top_k=top_k,
        )
        retrieval_fingerprint = compute_retrieval_fingerprint(retrieval_manifest)

    identity = DiagnosticRunIdentity(
        corpus_fingerprint=corpus_fingerprint,
        retrieval_fingerprint=retrieval_fingerprint,
        replay_plan_fingerprint=compute_replay_plan_fingerprint(
            plans,
            missing_rewrite_policy="original_proxy",
        ),
        diagnostic_contract_fingerprint=(
            compute_diagnostic_contract_fingerprint(
                semantic_thresholds=semantic_thresholds,
            )
        ),
    )
    report = run_context_duplicate_diagnostic(
        records=raw_records,
        retriever=retriever,
        chunks=chunks,
        corpus_source=corpus_source,
        corpus_fingerprint=corpus_fingerprint,
        retrieval_fingerprint=retrieval_fingerprint,
        top_k=top_k,
        requires_rewrite=cached_requires_rewrite,
        missing_rewrite_policy="original_proxy",
        semantic_similarity_provider=semantic_similarity_provider,
        semantic_thresholds=semantic_thresholds,
    )
    return ComposedDiagnosticRun(identity=identity, report=report)


__all__ = ["ComposedDiagnosticRun", "compose_diagnostic_run"]
