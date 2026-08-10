from types import SimpleNamespace

import pytest

from scripts.diagnostics.analyze_context_duplicates import compose_diagnostic_run


class _FakeRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return [SimpleNamespace(chunk_id="A", score=0.9)]


def _artifact() -> dict:
    return {
        "num_test_cases": 1,
        "num_skipped": 0,
        "results": [
            {
                "question": "Question",
                "category": "fact_lookup",
                "ticker": "AAPL",
                "section": None,
                "status": "OK",
                "context_precision": 0.4,
                "was_decomposed": False,
                "sub_queries": [],
            }
        ],
    }


def _chunks() -> list[dict]:
    return [
        {
            "chunk_id": "A",
            "text": "Evidence",
            "ticker": "AAPL",
            "section": "risk_factors",
            "accession_number": "filing",
            "chunk_index": 0,
        }
    ]


def _retrieval_manifest(corpus_fingerprint: str) -> dict:
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
            "corpus_fingerprint": corpus_fingerprint,
            "embedding_model_revision": "embedding-revision",
            "vector_dimension": 768,
            "distance_metric": "cosine",
            "build_version": "index-builder-v1",
            "snapshot_id": "snapshot-v1",
        },
    }


def test_cli_composition_builds_identity_and_runs_injected_dependencies() -> None:
    from scripts.diagnostics.diagnostic_fingerprints import compute_corpus_fingerprint

    chunks = _chunks()
    manifest = _retrieval_manifest(compute_corpus_fingerprint(chunks))
    retriever = _FakeRetriever()

    composed = compose_diagnostic_run(
        artifact=_artifact(),
        retriever=retriever,
        chunks=chunks,
        corpus_source="cloud",
        top_k=5,
        requires_rewrite=lambda question: False,
        semantic_similarity_provider=lambda replayed_chunks: {},
        semantic_thresholds=(0.95,),
        retrieval_manifest=manifest,
    )

    assert composed.identity.corpus_fingerprint.startswith("sha256:")
    assert composed.identity.retrieval_fingerprint.startswith("sha256:")
    assert composed.identity.replay_plan_fingerprint.startswith("sha256:")
    assert composed.identity.diagnostic_contract_fingerprint.startswith("sha256:")
    assert composed.report.metadata.corpus_source == "cloud"
    assert composed.report.metadata.corpus_fingerprint == (
        composed.identity.corpus_fingerprint
    )
    assert composed.report.metadata.retrieval_fingerprint == (
        composed.identity.retrieval_fingerprint
    )
    assert composed.report.metadata.missing_rewrite_policy == "original_proxy"
    assert composed.report.successful_replays == 1
    assert len(retriever.calls) == 1


def test_cli_composition_rejects_stale_index_manifest_before_retrieval() -> None:
    retriever = _FakeRetriever()
    manifest = _retrieval_manifest("sha256:stale-corpus")

    with pytest.raises(ValueError, match="corpus fingerprint"):
        compose_diagnostic_run(
            artifact=_artifact(),
            retriever=retriever,
            chunks=_chunks(),
            corpus_source="local",
            top_k=5,
            requires_rewrite=lambda question: False,
            semantic_similarity_provider=lambda replayed_chunks: {},
            retrieval_manifest=manifest,
        )

    assert retriever.calls == []


def test_cli_composition_marks_retrieval_identity_unknown_without_manifest() -> None:
    composed = compose_diagnostic_run(
        artifact=_artifact(),
        retriever=_FakeRetriever(),
        chunks=_chunks(),
        corpus_source="local",
        top_k=5,
        requires_rewrite=lambda question: False,
        semantic_similarity_provider=lambda replayed_chunks: {},
        retrieval_manifest=None,
    )

    assert composed.identity.corpus_fingerprint is not None
    assert composed.identity.retrieval_fingerprint is None


def test_cli_composition_rejects_incomplete_official_artifact() -> None:
    artifact = _artifact()
    artifact["num_skipped"] = 1
    retriever = _FakeRetriever()

    with pytest.raises(ValueError, match="skipped records"):
        compose_diagnostic_run(
            artifact=artifact,
            retriever=retriever,
            chunks=_chunks(),
            corpus_source="local",
            top_k=5,
            requires_rewrite=lambda question: False,
            semantic_similarity_provider=lambda replayed_chunks: {},
            retrieval_manifest=None,
        )

    assert retriever.calls == []

