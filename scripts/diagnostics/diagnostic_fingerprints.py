"""Deterministic identities and comparability rules for diagnostic runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

from scripts.diagnostics.context_duplicate_metrics import (
    ELIGIBLE_REPLAY_FIDELITIES,
    LOW_CONTEXT_PRECISION_THRESHOLD,
)
from scripts.diagnostics.replay_contract import EvaluationReplayPlan
from src.retrieval.index_manifest import compute_corpus_fingerprint

RETRIEVAL_FINGERPRINT_SCHEMA_VERSION = 1
REPLAY_PLAN_FINGERPRINT_SCHEMA_VERSION = 1
DIAGNOSTIC_CONTRACT_FINGERPRINT_SCHEMA_VERSION = 1

REQUIRED_RETRIEVAL_FIELDS = frozenset(
    {
        "retrieval_code_digest",
        "embedding_model",
        "cross_encoder_model",
        "bm25",
        "candidate_pool",
        "top_k",
        "rrf",
        "score_filter_rules",
        "structured_lookup_rules_digest",
        "filter_behavior_digest",
        "qdrant",
        "query_rewrite_policy",
        "decomposition_merge_policy",
        "index_manifest",
    }
)
REQUIRED_INDEX_MANIFEST_FIELDS = frozenset(
    {
        "corpus_fingerprint",
        "embedding_model_revision",
        "vector_dimension",
        "distance_metric",
        "build_version",
        "snapshot_id",
    }
)


@dataclass(frozen=True)
class DiagnosticRunIdentity:
    corpus_fingerprint: str | None
    retrieval_fingerprint: str | None
    replay_plan_fingerprint: str | None
    diagnostic_contract_fingerprint: str | None


@dataclass(frozen=True)
class RunComparability:
    status: Literal[
        "strictly_comparable",
        "controlled_retrieval_comparison",
        "not_comparable",
        "unknown",
    ]
    differing_components: tuple[str, ...]


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _reject_unknown_provenance(value: Any, *, path: str) -> None:
    if value is None or value == "":
        raise ValueError(f"Retrieval manifest contains null provenance at {path}")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError(f"Retrieval manifest contains non-finite value at {path}")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"Retrieval manifest key at {path} must be a string")
            _reject_unknown_provenance(nested, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_unknown_provenance(nested, path=f"{path}[{index}]")
    elif not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"Unsupported retrieval manifest value at {path}")


def compute_retrieval_fingerprint(manifest: Mapping[str, Any]) -> str:
    """Hash a complete retrieval and trusted index-build manifest."""
    missing_fields = REQUIRED_RETRIEVAL_FIELDS - manifest.keys()
    if missing_fields:
        raise ValueError(
            f"Retrieval manifest is missing required fields: {sorted(missing_fields)}"
        )
    index_manifest = manifest.get("index_manifest")
    if not isinstance(index_manifest, Mapping):
        raise ValueError("Retrieval index_manifest must be an object")
    missing_index_fields = REQUIRED_INDEX_MANIFEST_FIELDS - index_manifest.keys()
    if missing_index_fields:
        raise ValueError(
            "Retrieval index_manifest is missing required fields: "
            f"{sorted(missing_index_fields)}"
        )
    _reject_unknown_provenance(manifest, path="retrieval_manifest")
    return _hash_payload(
        {
            "schema_version": RETRIEVAL_FINGERPRINT_SCHEMA_VERSION,
            "manifest": manifest,
        }
    )


def compute_replay_plan_fingerprint(
    plans: Sequence[EvaluationReplayPlan],
    *,
    missing_rewrite_policy: Literal["original_proxy", "regenerate"],
) -> str:
    canonical_plans = []
    for plan in plans:
        canonical_plans.append(
            {
                "original_question": plan.original_question,
                "category": plan.category,
                "ticker": plan.ticker,
                "section": plan.section,
                "official_context_precision": plan.official_context_precision,
                "route": plan.route,
                "evaluation_case_fingerprint": plan.evaluation_case_fingerprint,
                "queries": [
                    {
                        "effective_query": query.effective_query,
                        "query_source": query.query_source,
                        "ticker": query.ticker,
                        "section": query.section,
                        "historical_num_chunks": query.historical_num_chunks,
                    }
                    for query in plan.query_plans
                ],
            }
        )
    return _hash_payload(
        {
            "schema_version": REPLAY_PLAN_FINGERPRINT_SCHEMA_VERSION,
            "missing_rewrite_policy": missing_rewrite_policy,
            "plans": canonical_plans,
        }
    )


def compute_diagnostic_contract_fingerprint(
    *,
    semantic_thresholds: Sequence[float],
) -> str:
    thresholds = sorted(set(float(threshold) for threshold in semantic_thresholds))
    if any(not isfinite(threshold) or not 0.0 <= threshold <= 1.0 for threshold in thresholds):
        raise ValueError("Semantic thresholds must be finite values between 0 and 1")
    return _hash_payload(
        {
            "schema_version": DIAGNOSTIC_CONTRACT_FINGERPRINT_SCHEMA_VERSION,
            "semantic_thresholds": thresholds,
            "low_context_precision_threshold": LOW_CONTEXT_PRECISION_THRESHOLD,
            "eligible_replay_fidelities": sorted(ELIGIBLE_REPLAY_FIDELITIES),
            "exact_duplicate_formula": "distinct-id-normalized-text-v1",
            "adjacent_formula": "same-filing-section-neighbor-index-v1",
            "containment_formula": "multiset-five-gram-shorter-denominator-v1",
            "semantic_formula": "cosine-semantic-only-v1",
            "pairwise_overlap_formula": "shared-adjacent-five-grams-v1",
        }
    )


def assess_run_comparability(
    first: DiagnosticRunIdentity,
    second: DiagnosticRunIdentity,
) -> RunComparability:
    components = (
        "corpus_fingerprint",
        "retrieval_fingerprint",
        "replay_plan_fingerprint",
        "diagnostic_contract_fingerprint",
    )
    if any(
        getattr(identity, component) is None
        for identity in (first, second)
        for component in components
    ):
        return RunComparability("unknown", ())

    differing = tuple(
        component
        for component in components
        if getattr(first, component) != getattr(second, component)
    )
    if not differing:
        return RunComparability("strictly_comparable", ())
    if differing == ("retrieval_fingerprint",):
        return RunComparability("controlled_retrieval_comparison", differing)
    return RunComparability("not_comparable", differing)
