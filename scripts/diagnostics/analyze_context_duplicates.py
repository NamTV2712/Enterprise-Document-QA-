"""Runtime composition entry point for context-duplicate diagnostics."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from itertools import combinations
from math import sqrt
from pathlib import Path
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
from configs.settings import settings
from src.memory.query_rewriter import needs_financial_expansion
from src.retrieval.chunk_loader import load_retrieval_chunks
from src.retrieval.embedder import Embedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.vector_store import VectorStore


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


def _pairwise_semantic_similarities(
    embedder: Embedder,
    chunks: tuple[dict[str, Any], ...],
) -> Mapping[tuple[str, str], float]:
    """Return cosine similarity for all distinct final-context chunk pairs."""
    if len(chunks) < 2:
        return {}

    vectors = embedder.embed_documents([chunk["text"] for chunk in chunks])
    norms = [sqrt(sum(value * value for value in vector)) for vector in vectors]
    similarities: dict[tuple[str, str], float] = {}
    for (left_index, left_chunk), (right_index, right_chunk) in combinations(
        enumerate(chunks), 2
    ):
        denominator = norms[left_index] * norms[right_index]
        similarity = (
            sum(
                left * right
                for left, right in zip(
                    vectors[left_index], vectors[right_index], strict=True
                )
            )
            / denominator
            if denominator
            else 0.0
        )
        similarities[(left_chunk["chunk_id"], right_chunk["chunk_id"])] = similarity
    return similarities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("data/evaluation_results_v2.json"),
        help="Completed evaluation artifact with no skipped cases.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/diagnostics/context_duplicate_report.json"),
        help="Destination for the replay report (JSON).",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--retrieval-manifest",
        type=Path,
        default=None,
        help=(
            "Optional complete retrieval provenance manifest. Without it, the "
            "report is descriptive but not strictly comparable to later runs."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    if not isinstance(artifact, dict):
        raise ValueError("Evaluation artifact root must be an object")
    retrieval_manifest = None
    if args.retrieval_manifest is not None:
        retrieval_manifest = json.loads(
            args.retrieval_manifest.read_text(encoding="utf-8")
        )
        if not isinstance(retrieval_manifest, dict):
            raise ValueError("Retrieval manifest root must be an object")

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
        chunks = load_retrieval_chunks(store, settings.data_processed_dir)
        retriever = HybridRetriever(embedder=embedder, store=store, all_chunks=chunks)
        composed = compose_diagnostic_run(
            artifact=artifact,
            retriever=retriever,
            chunks=chunks,
            corpus_source=store.mode,
            top_k=args.top_k,
            requires_rewrite=needs_financial_expansion,
            semantic_similarity_provider=lambda replayed_chunks: (
                _pairwise_semantic_similarities(embedder, replayed_chunks)
            ),
            retrieval_manifest=retrieval_manifest,
        )

    payload = asdict(composed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = composed.report
    print(f"Wrote {args.output}")
    print(
        "Replays: "
        f"{report.successful_replays}/{report.planned_cases}; "
        f"primary eligible: {report.primary_eligible_cases}/"
        f"{report.planned_primary_eligible_cases}; failures: {len(report.failures)}"
    )
    print(f"Corpus fingerprint: {composed.identity.corpus_fingerprint}")
    print(f"Retrieval fingerprint: {composed.identity.retrieval_fingerprint}")


if __name__ == "__main__":
    main()
