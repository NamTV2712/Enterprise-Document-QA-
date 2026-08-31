"""Provider-free audit for the intent-first context-packing counterfactual.

The candidate changes only summary and comparative packing.  It is compared
with the admitted ``selective_packed_v2`` policy on the frozen Phase 1
artifact; no labels are used to choose evidence, and no provider calls are
made.  Passing this audit means the candidate is safe to take to a small
provider sentinel, not that it is ready for promotion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import tiktoken

from scripts.diagnostics.comparative_packing_v3 import (
    _source_boundaries_match,
    _term_coverage,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V3,
    CONTEXT_STRATEGY_SELECTIVE_V4,
    effective_case_context_strategy,
    pack_case_context,
    render_packed_blocks,
)
from src.evaluation.evidence_contracts import (
    branch_evidence_terms,
    evidence_terms,
)
from src.evaluation.generation_checkpoint import build_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.comparative_context import (
    COMPARATIVE_INTENT_FIRST_FINGERPRINT,
)
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT


EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:1ad021ce72af2116f9b4f7ad780d5c6e809fd5a01e46d30d0ae4bfecd62599d9"
)
EXPECTED_CASES = 30
EXPECTED_SUMMARY_CASES = 6
EXPECTED_COMPARATIVE_CASES = 6

CYBER_QUESTION = (
    "Compare the cybersecurity risk disclosures of Apple, Microsoft, and Amazon."
)
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)

EXPECTED_TARGET_KEPT = {
    CYBER_QUESTION: {"AMZN_000101872426000004_risk_factors_0012"},
    AWS_QUESTION: {"MSFT_000095017025100235_mdna_0001"},
}


def _unique_ids(chunks: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(chunk.get("chunk_id") for chunk in chunks))


def _branch_rows(
    case_payload: dict[str, Any], kept_ids: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    question = case_payload["question"]
    for query_entry in case_payload.get("queries", []):
        query = query_entry.get("query", {})
        available = _unique_ids(query_entry.get("chunks", []))
        kept = [chunk_id for chunk_id in available if chunk_id in kept_ids]
        ticker = query.get("ticker")
        terms = branch_evidence_terms(question, ticker)
        branch_text = " ".join(
            chunk.get("text", "")
            for chunk in query_entry.get("chunks", [])
            if chunk.get("chunk_id") in kept_ids
        )
        coverage = _term_coverage(terms, branch_text)
        rows.append(
            {
                "ticker": ticker,
                "effective_query": query.get("effective_query"),
                "available_chunk_ids": available,
                "kept_chunk_ids": kept,
                "representative_kept": bool(kept),
                "top_one_kept": not available or available[0] in kept_ids,
                "required_terms": list(terms),
                "required_term_coverage": coverage,
                "contract_passed": all(coverage.values()),
            }
        )
    return rows


def _measure_case(
    case_payload: dict[str, Any],
    required_keywords: list[str],
    encoder: Any,
    candidate_strategy: str = CONTEXT_STRATEGY_SELECTIVE_V3,
) -> dict[str, Any]:
    full_rendered = build_evidence_context(case_payload)
    baseline = pack_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=effective_case_context_strategy(
            CONTEXT_STRATEGY_SELECTIVE_V2, case_payload.get("category", "")
        ),
    )
    candidate = pack_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=candidate_strategy,
    )
    baseline_rendered = render_packed_blocks(baseline)
    candidate_rendered = render_packed_blocks(candidate)
    terms = evidence_terms(case_payload["question"], required_keywords)
    full_coverage = _term_coverage(terms, full_rendered)
    candidate_coverage = _term_coverage(terms, candidate_rendered)
    full_ids = set(_unique_ids([
        chunk
        for query_entry in case_payload.get("queries", [])
        for chunk in query_entry.get("chunks", [])
    ]))
    structured_ids = {
        chunk.get("chunk_id")
        for query_entry in case_payload.get("queries", [])
        for chunk in query_entry.get("chunks", [])
        if isinstance(chunk.get("score"), (int, float))
        and chunk["score"] >= 10.0
    }
    category = case_payload.get("category")
    candidate_ids = set(candidate.kept_ids)
    branches = _branch_rows(case_payload, candidate_ids)
    return {
        "question": case_payload["question"],
        "category": category,
        "baseline_strategy": effective_case_context_strategy(
            CONTEXT_STRATEGY_SELECTIVE_V2, category or ""
        ),
        "candidate_strategy": effective_case_context_strategy(
            CONTEXT_STRATEGY_SELECTIVE_V3, category or ""
        ),
        "full_chunks": len(full_ids),
        "baseline_chunks": len(baseline.kept),
        "candidate_chunks": len(candidate.kept),
        "full_tokens": len(encoder.encode(full_rendered)),
        "baseline_tokens": len(encoder.encode(baseline_rendered)),
        "candidate_tokens": len(encoder.encode(candidate_rendered)),
        "candidate_token_delta": len(encoder.encode(candidate_rendered))
        - len(encoder.encode(baseline_rendered)),
        "required_terms": list(terms),
        "full_coverage": full_coverage,
        "candidate_coverage": candidate_coverage,
        "candidate_evidence_coverage_passed": (
            all(full_coverage.values()) and candidate_coverage == full_coverage
        ),
        "candidate_source_boundaries_passed": _source_boundaries_match(
            candidate_rendered, candidate.kept
        ),
        "candidate_subset_of_full": candidate_ids.issubset(full_ids),
        "structured_hits_preserved": structured_ids.issubset(candidate_ids),
        "non_target_identity": (
            category in {"summary", "comparative"}
            or baseline.kept_ids == candidate.kept_ids
        ),
        "changed": baseline.kept_ids != candidate.kept_ids,
        "baseline_chunk_ids": baseline.kept_ids,
        "candidate_chunk_ids": candidate.kept_ids,
        "branches": branches if category == "comparative" else [],
        "branch_representatives_passed": (
            all(row["representative_kept"] for row in branches)
            if category == "comparative"
            else True
        ),
        "branch_contracts_passed": (
            all(row["contract_passed"] for row in branches)
            if category == "comparative"
            else True
        ),
    }


def run(
    artifact_path: Path,
    priority: int = 2,
    candidate_strategy: str = CONTEXT_STRATEGY_SELECTIVE_V3,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    embedded = artifact.get("fingerprints", {}).get("artifact")
    if embedded != EXPECTED_ARTIFACT_FINGERPRINT:
        raise RuntimeError(
            f"Artifact fingerprint drift: expected {EXPECTED_ARTIFACT_FINGERPRINT}, "
            f"found {embedded}"
        )

    metadata = {case.question: case for case in TEST_SET}
    encoder = tiktoken.get_encoding("cl100k_base")
    rows = [
        _measure_case(
            payload,
            metadata[payload["question"]].required_keywords,
            encoder,
            candidate_strategy,
        )
        for payload in artifact.get("cases", [])
        if payload["question"] in metadata
        and metadata[payload["question"]].priority <= priority
    ]
    rows.sort(key=lambda row: row["question"])
    summaries = [row for row in rows if row["category"] == "summary"]
    comparative = [row for row in rows if row["category"] == "comparative"]
    non_target = [
        row for row in rows if row["category"] not in {"summary", "comparative"}
    ]
    baseline_tokens = sum(row["baseline_tokens"] for row in rows)
    candidate_tokens = sum(row["candidate_tokens"] for row in rows)
    target_rows = {
        row["question"]: row for row in rows if row["question"] in EXPECTED_TARGET_KEPT
    }
    target_kept_passed = all(
        expected.issubset(set(target_rows[question]["candidate_chunk_ids"]))
        for question, expected in EXPECTED_TARGET_KEPT.items()
        if question in target_rows
    ) and len(target_rows) == len(EXPECTED_TARGET_KEPT)
    report: dict[str, Any] = {
        "schema_version": 1,
        "audit": (
            "context_precision_counterfactual_v4"
            if candidate_strategy == CONTEXT_STRATEGY_SELECTIVE_V4
            else "context_precision_counterfactual_v3"
        ),
        "provider_calls": 0,
        "artifact_fingerprint": embedded,
        "query_shaper_fingerprint": QUERY_SHAPER_FINGERPRINT,
        "comparative_selector_fingerprint": COMPARATIVE_INTENT_FIRST_FINGERPRINT,
        "baseline_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "candidate_strategy": candidate_strategy,
        "pre_registered_gates": {
            "expected_cases": EXPECTED_CASES,
            "expected_summary_cases": EXPECTED_SUMMARY_CASES,
            "expected_comparative_cases": EXPECTED_COMPARATIVE_CASES,
            "candidate_is_subset_of_frozen_evidence": True,
            "candidate_preserves_structured_hits": True,
            "candidate_preserves_required_term_coverage": True,
            "candidate_preserves_comparative_branch_representatives": True,
            "candidate_preserves_branch_fact_contracts": True,
            "non_target_context_identity": True,
            "candidate_tokens_not_above_baseline": True,
            "target_donor_findings_preserved": True,
        },
        "num_cases": len(rows),
        "num_summary_cases": len(summaries),
        "num_comparative_cases": len(comparative),
        "evidence_coverage_cases": sum(
            row["candidate_evidence_coverage_passed"] for row in rows
        ),
        "source_boundary_cases": sum(
            row["candidate_source_boundaries_passed"] for row in rows
        ),
        "frozen_subset_cases": sum(row["candidate_subset_of_full"] for row in rows),
        "structured_hit_cases": sum(row["structured_hits_preserved"] for row in rows),
        "non_target_identity_cases": sum(row["non_target_identity"] for row in non_target),
        "comparative_representative_cases": sum(
            row["branch_representatives_passed"] for row in comparative
        ),
        "comparative_contract_cases": sum(
            row["branch_contracts_passed"] for row in comparative
        ),
        "target_donor_findings_passed": target_kept_passed,
        "changed_cases": sum(row["changed"] for row in rows),
        "baseline_tokens": baseline_tokens,
        "candidate_tokens": candidate_tokens,
        "candidate_token_delta": candidate_tokens - baseline_tokens,
        "cases": rows,
    }
    report["passed"] = (
        report["num_cases"] == EXPECTED_CASES
        and report["num_summary_cases"] == EXPECTED_SUMMARY_CASES
        and report["num_comparative_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["evidence_coverage_cases"] == EXPECTED_CASES
        and report["source_boundary_cases"] == EXPECTED_CASES
        and report["frozen_subset_cases"] == EXPECTED_CASES
        and report["structured_hit_cases"] == EXPECTED_CASES
        and report["non_target_identity_cases"] == len(non_target)
        and report["comparative_representative_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and report["comparative_contract_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["target_donor_findings_passed"]
        and report["changed_cases"] > 0
        and report["candidate_token_delta"] <= 0
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("data/eval_artifacts/phase1_priority2.json"),
    )
    parser.add_argument("--priority", type=int, default=2)
    parser.add_argument(
        "--candidate-strategy",
        choices=[CONTEXT_STRATEGY_SELECTIVE_V3, CONTEXT_STRATEGY_SELECTIVE_V4],
        default=CONTEXT_STRATEGY_SELECTIVE_V3,
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run(args.artifact, args.priority, args.candidate_strategy)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
