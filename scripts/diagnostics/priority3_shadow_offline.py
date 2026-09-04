"""Audit the Priority-3 Shadow v1 artifact without provider calls.

This diagnostic is intentionally artifact-first.  It checks the exact test
scope, static plan provenance, evidence boundaries, deterministic retrieval
metrics, and current local retrieval fingerprints before any Phase 2 provider
run is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts.run_evaluation_phase2 import OFFICIAL_SELECTIVE_V2_RESULTS_PATH
from src.evaluation.generation_checkpoint import (
    build_evidence_context,
    parse_evidence_context,
)
from src.evaluation.p3_shadow_plan import (
    P3_SHADOW_PLAN_FINGERPRINT,
    P3_SHADOW_PLANS,
    validate_priority3_shadow_plans,
)
from src.evaluation.retrieval_artifact import (
    _embedding_fingerprint,
    _reranker_fingerprint,
    canonical_json,
    compute_index_manifest_fingerprint,
)
from src.evaluation.test_case_selector import select_test_cases
from src.evaluation.test_set import TEST_SET
from src.evaluation.evaluator import compute_recall_proxy
from src.retrieval.index_manifest import compute_corpus_fingerprint
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT

DEFAULT_ARTIFACT = Path("data/eval_artifacts/phase1_priority3_shadow_v1.json")
DEFAULT_OUTPUT = Path("data/diagnostics/priority3_shadow_v1_offline.json")
OFFICIAL_N30_SHA256 = (
    "a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _sha256_payload(value: Any) -> str:
    return _sha256_bytes(canonical_json(value))


def _selected_recall(case_payload: dict[str, Any], required: list[str]) -> float | None:
    chunks: list[SimpleNamespace] = []
    seen: set[str] = set()
    for query in case_payload.get("queries", []):
        for chunk in query.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            chunks.append(SimpleNamespace(text=chunk.get("text", "")))
    return compute_recall_proxy(required, chunks)


def _source_roundtrip(case_payload: dict[str, Any]) -> bool:
    context = build_evidence_context(case_payload)
    sources = parse_evidence_context(context)
    unique_ids = {
        chunk.get("chunk_id")
        for query in case_payload.get("queries", [])
        for chunk in query.get("chunks", [])
    }
    if len(sources) != len(unique_ids) or not sources:
        return False
    reconstructed = "\n\n".join(
        f"[Source {source['number']}] {source['citation']}\n{source['text']}"
        for source in sources
    )
    return reconstructed == context


def run(
    *,
    artifact_path: Path = DEFAULT_ARTIFACT,
    output: Path | None = DEFAULT_OUTPUT,
    official_path: Path = OFFICIAL_SELECTIVE_V2_RESULTS_PATH,
) -> dict[str, Any]:
    artifact_bytes = artifact_path.read_bytes()
    artifact = json.loads(artifact_bytes.decode("utf-8"))
    selected = select_test_cases(TEST_SET, priority=3, exact_priority=True)
    expected_by_question = {case.question: case for case in selected.cases}
    artifact_cases = artifact.get("cases") or []
    artifact_by_question = {
        case.get("question"): case for case in artifact_cases
    }
    rows: list[dict[str, Any]] = []
    for question, test_case in expected_by_question.items():
        payload = artifact_by_question.get(question) or {}
        recall = _selected_recall(payload, test_case.required_keywords)
        rows.append({
            "question": question,
            "category": test_case.category,
            "ticker": test_case.ticker,
            "required_keyword_count": len(test_case.required_keywords),
            "recall_proxy": recall,
            "source_boundary_roundtrip": _source_roundtrip(payload),
            "query_count": len(payload.get("queries", [])),
            "returned_chunk_count": len(payload.get("final_chunk_ids", [])),
        })

    actual_tickers = {
        query.get("query", {}).get("ticker")
        for case in artifact_cases
        for query in case.get("queries", [])
        if query.get("query", {}).get("ticker")
    }
    expected_tickers = {
        query.ticker
        for plan in P3_SHADOW_PLANS
        for query in plan.queries
        if query.ticker
    }
    category_distribution = dict(
        sorted(Counter(case.get("category") for case in artifact_cases).items())
    )
    expected_distribution = {
        "comparative": 1,
        "enumeration": 1,
        "fact_lookup": 9,
        "multi_hop": 5,
        "summary": 6,
    }
    fingerprints = artifact.get("fingerprints") or {}
    current_fingerprints = {
        "corpus": (
            (json.loads(Path("data/processed/qdrant_index_manifest.json").read_text(encoding="utf-8")))
            .get("corpus_fingerprint")
        ),
        "index_manifest": compute_index_manifest_fingerprint(None),
        "embedding": _embedding_fingerprint(),
        "reranker": _reranker_fingerprint(),
        "query_shaper": QUERY_SHAPER_FINGERPRINT,
        "lexical_ladder": LEXICAL_LADDER_FINGERPRINT,
    }
    fingerprint_match = all(
        fingerprints.get(name) == value
        for name, value in current_fingerprints.items()
    )
    official_sha = hashlib.sha256(official_path.read_bytes()).hexdigest()
    provenance = artifact.get("provenance") or {}
    selection = artifact.get("selection") or {}
    plan_questions = [plan.get("question") for plan in artifact.get("plans", [])]
    query_values = [
        query.get("effective_query", "")
        for plan in artifact.get("plans", [])
        for query in plan.get("queries", [])
    ]
    comparative = artifact_by_question.get(
        "Compare Visa and Mastercard's business risk factors.", {}
    )
    comparative_branches = [
        {
            "ticker": query.get("query", {}).get("ticker"),
            "section": query.get("query", {}).get("section"),
            "has_evidence": bool(query.get("chunks")),
        }
        for query in comparative.get("queries", [])
    ]
    keyword_rows = [row for row in rows if row["required_keyword_count"]]
    gates = {
        "exact_p3_case_count": len(artifact_cases) == 22 and len(rows) == 22,
        "no_p1_p2_cases": all(
            question in expected_by_question for question in artifact_by_question
        ),
        "ticker_count": len(actual_tickers) == 15 and actual_tickers == expected_tickers,
        "category_distribution": category_distribution == expected_distribution,
        "plan_count_and_coverage": (
            len(artifact.get("plans", [])) == 22
            and plan_questions == [case.question for case in selected.cases]
            and len(set(plan_questions)) == 22
        ),
        "all_queries_non_empty": bool(query_values) and all(value.strip() for value in query_values),
        "all_queries_returned_evidence": all(row["returned_chunk_count"] > 0 for row in rows),
        "keyword_bearing_recall_1": (
            len(keyword_rows) == 21
            and all(row["recall_proxy"] == 1.0 for row in keyword_rows)
        ),
        "visa_mastercard_branch_evidence": (
            [(row["ticker"], row["section"]) for row in comparative_branches]
            == [("V", "risk_factors"), ("MA", "risk_factors")]
            and all(row["has_evidence"] for row in comparative_branches)
        ),
        "source_boundary_roundtrip": all(row["source_boundary_roundtrip"] for row in rows),
        "current_retrieval_fingerprints": fingerprint_match,
        "artifact_determinism_verified": provenance.get("determinism_verified") is True,
        "no_provider_calls": (
            provenance.get("provider_calls") == 0
            and provenance.get("offline_socket_guard") is True
        ),
        "static_plan_is_ground_truth_independent": (
            provenance.get("provider_planner_used") is False
            and provenance.get("ground_truth_used") is False
            and fingerprints.get("plan") == P3_SHADOW_PLAN_FINGERPRINT
        ),
        "selection_scope_provenance": (
            selection.get("selector") == "shared_test_case_selector_v1"
            and selection.get("selection_scope") == "priority == 3"
            and selection.get("exact_priority") is True
            and selection.get("selected_case_count") == 22
        ),
        "official_n30_unchanged": official_sha == OFFICIAL_N30_SHA256,
    }
    try:
        validate_priority3_shadow_plans(P3_SHADOW_PLANS)
        gates["static_plan_contract"] = True
    except (TypeError, ValueError):
        gates["static_plan_contract"] = False

    report = {
        "schema_version": 1,
        "audit": "priority3_shadow_v1_offline",
        "official": False,
        "promotion_eligible": False,
        "artifact_path": str(artifact_path),
        "artifact_file_sha256": _sha256_bytes(artifact_bytes),
        "artifact_embedded_fingerprint": fingerprints.get("artifact"),
        "selection": selection,
        "category_distribution": category_distribution,
        "ticker_count": len(actual_tickers),
        "tickers": sorted(actual_tickers),
        "keyword_bearing_cases": len(keyword_rows),
        "keyword_bearing_recall": (
            sum(row["recall_proxy"] == 1.0 for row in keyword_rows) / len(keyword_rows)
            if keyword_rows else None
        ),
        "comparative_branches": comparative_branches,
        "current_fingerprints": current_fingerprints,
        "fingerprints": fingerprints,
        "rows": rows,
        "official_n30_sha256": official_sha,
        "gates": gates,
        "passed": all(gates.values()),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(artifact_path=args.artifact, output=args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
