import pytest

from scripts.diagnostics.diagnostic_fingerprints import (
    DiagnosticRunIdentity,
    assess_run_comparability,
    compute_corpus_fingerprint,
    compute_diagnostic_contract_fingerprint,
    compute_replay_plan_fingerprint,
    compute_retrieval_fingerprint,
)
from scripts.diagnostics.replay_contract import EvaluationReplayPlan, ReplayQueryPlan


def _chunk(chunk_id: str, text: str, *, chunk_index: int) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "ticker": "AAPL",
        "section": "risk_factors",
        "accession_number": "filing",
        "chunk_index": chunk_index,
    }


def _retrieval_manifest() -> dict:
    return {
        "retrieval_code_digest": "code-sha256",
        "embedding_model": {
            "id": "nomic-ai/nomic-embed-text-v1.5",
            "revision": "embedding-revision",
            "dimension": 768,
        },
        "cross_encoder_model": {
            "id": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "revision": "reranker-revision",
        },
        "bm25": {"tokenizer": "lower-alnum-v1", "parameters": {}},
        "candidate_pool": 10,
        "top_k": 5,
        "rrf": {"k": 60, "dense_weight": 1.0, "bm25_weight": 1.0},
        "score_filter_rules": {"cross_encoder_relative_cutoff": 0.5},
        "structured_lookup_rules_digest": "structured-sha256",
        "filter_behavior_digest": "filter-sha256",
        "qdrant": {"distance": "cosine", "search_params": {}},
        "query_rewrite_policy": "original_proxy",
        "decomposition_merge_policy": "plan-order-first-occurrence-v1",
        "index_manifest": {
            "corpus_fingerprint": "corpus-sha256",
            "embedding_model_revision": "embedding-revision",
            "vector_dimension": 768,
            "distance_metric": "cosine",
            "build_version": "index-builder-v1",
            "snapshot_id": "index-snapshot-v1",
        },
    }


def _replay_plan(query: str = "Question") -> EvaluationReplayPlan:
    return EvaluationReplayPlan(
        original_question="Question",
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        official_context_precision=0.4,
        route="direct",
        query_plans=(
            ReplayQueryPlan(
                effective_query=query,
                query_source="original_question",
                ticker="AAPL",
                section=None,
            ),
        ),
        evaluation_case_fingerprint="case-v1",
    )


def test_corpus_fingerprint_is_order_and_storage_artifact_independent() -> None:
    first = _chunk("A", "Revenue\r\n grew   strongly.", chunk_index=0)
    first["embedding"] = [0.1, 0.2]
    first["source_path"] = "local/path.jsonl"
    second = _chunk("B", "Risk evidence", chunk_index=1)

    local_fingerprint = compute_corpus_fingerprint([second, first])
    cloud_fingerprint = compute_corpus_fingerprint(
        [
            _chunk("A", "Revenue grew strongly.", chunk_index=0),
            _chunk("B", "Risk evidence", chunk_index=1),
        ]
    )

    assert local_fingerprint == cloud_fingerprint
    assert local_fingerprint.startswith("sha256:")


def test_corpus_fingerprint_changes_with_retrieval_relevant_content() -> None:
    baseline = [_chunk("A", "Revenue grew.", chunk_index=0)]

    assert compute_corpus_fingerprint(baseline) != compute_corpus_fingerprint(
        [_chunk("A", "Revenue declined.", chunk_index=0)]
    )
    assert compute_corpus_fingerprint(baseline) != compute_corpus_fingerprint(
        [_chunk("A", "Revenue grew.", chunk_index=1)]
    )


def test_corpus_fingerprint_rejects_duplicate_logical_chunks() -> None:
    with pytest.raises(ValueError, match="duplicate chunk IDs"):
        compute_corpus_fingerprint(
            [
                _chunk("A", "first", chunk_index=0),
                _chunk("A", "second", chunk_index=1),
            ]
        )


def test_retrieval_fingerprint_is_canonical_and_sensitive_to_config() -> None:
    manifest = _retrieval_manifest()
    reordered = dict(reversed(list(manifest.items())))

    assert compute_retrieval_fingerprint(manifest) == compute_retrieval_fingerprint(
        reordered
    )

    changed = _retrieval_manifest()
    changed["candidate_pool"] = 20
    assert compute_retrieval_fingerprint(manifest) != compute_retrieval_fingerprint(
        changed
    )


def test_retrieval_fingerprint_rejects_unknown_model_or_index_provenance() -> None:
    missing_revision = _retrieval_manifest()
    missing_revision["embedding_model"]["revision"] = None
    with pytest.raises(ValueError, match="null provenance"):
        compute_retrieval_fingerprint(missing_revision)

    missing_snapshot = _retrieval_manifest()
    del missing_snapshot["index_manifest"]["snapshot_id"]
    with pytest.raises(ValueError, match="index_manifest"):
        compute_retrieval_fingerprint(missing_snapshot)


def test_replay_and_diagnostic_fingerprints_cover_policy_and_thresholds() -> None:
    plan = _replay_plan()

    assert compute_replay_plan_fingerprint(
        [plan],
        missing_rewrite_policy="original_proxy",
    ) != compute_replay_plan_fingerprint(
        [plan],
        missing_rewrite_policy="regenerate",
    )
    assert compute_replay_plan_fingerprint(
        [plan],
        missing_rewrite_policy="original_proxy",
    ) != compute_replay_plan_fingerprint(
        [_replay_plan("Changed query")],
        missing_rewrite_policy="original_proxy",
    )
    assert compute_diagnostic_contract_fingerprint(
        semantic_thresholds=(0.90, 0.95),
    ) != compute_diagnostic_contract_fingerprint(
        semantic_thresholds=(0.95,),
    )


def test_run_comparability_distinguishes_strict_controlled_and_unknown() -> None:
    baseline = DiagnosticRunIdentity(
        corpus_fingerprint="corpus",
        retrieval_fingerprint="retrieval-a",
        replay_plan_fingerprint="plans",
        diagnostic_contract_fingerprint="diagnostic",
    )

    assert assess_run_comparability(baseline, baseline).status == (
        "strictly_comparable"
    )
    controlled = DiagnosticRunIdentity(
        corpus_fingerprint="corpus",
        retrieval_fingerprint="retrieval-b",
        replay_plan_fingerprint="plans",
        diagnostic_contract_fingerprint="diagnostic",
    )
    assert assess_run_comparability(baseline, controlled).status == (
        "controlled_retrieval_comparison"
    )
    unknown = DiagnosticRunIdentity(
        corpus_fingerprint="corpus",
        retrieval_fingerprint=None,
        replay_plan_fingerprint="plans",
        diagnostic_contract_fingerprint="diagnostic",
    )
    assert assess_run_comparability(baseline, unknown).status == "unknown"

