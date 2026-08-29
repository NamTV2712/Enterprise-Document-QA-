"""Deterministic gate for oracle-free comparative context selection.

This diagnostic checks the v5 selector against the active frozen artifact. It
uses the same generic selector shape as the production adapter and never uses
test-set facts to choose a chunk. Evaluation contracts are consulted only
after selection to score coverage and known findings.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import tiktoken

from scripts.diagnostics.comparative_packing_v3 import (
    _source_boundaries_match,
    _term_coverage,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V5,
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
    COMPARATIVE_SELECTOR_FINGERPRINT,
    ComparativeBranch,
    select_comparative_chunks,
)
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT


EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:9869912195606125b0a7efe56f091662fd50d48e08c92141415c1a174ffd0c98"
)
EXPECTED_CASES = 30
EXPECTED_COMPARATIVE_CASES = 6
MIN_COMPARATIVE_TOKEN_REDUCTION_PCT = 60.0
SELECTOR_FINGERPRINT = COMPARATIVE_SELECTOR_FINGERPRINT

CYBER_QUESTION = (
    "Compare the cybersecurity risk disclosures of Apple, Microsoft, and Amazon."
)
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
INTERNATIONAL_QUESTION = (
    "Compare Apple's and Amazon's approach to international operations risk."
)

REQUIRED_KEPT_CHUNKS = {
    CYBER_QUESTION: {"AMZN_000101872426000004_risk_factors_0012"},
    AWS_QUESTION: {"MSFT_000095017025100235_mdna_0001"},
}
REQUIRED_DROPPED_CHUNKS = {
    INTERNATIONAL_QUESTION: {
        "AAPL_000032019325000079_risk_factors_0007",
    },
}


def _unique_ids(chunks: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(chunk.get("chunk_id") for chunk in chunks))


def _runtime_selected_ids(case_payload: dict[str, Any]) -> list[str]:
    branches = []
    for query_entry in case_payload.get("queries", []):
        query = query_entry.get("query", {})
        chunks = [SimpleNamespace(**chunk) for chunk in query_entry.get("chunks", [])]
        branches.append(
            ComparativeBranch(
                query=(
                    query.get("effective_query")
                    or query.get("retrieval_query")
                    or ""
                ),
                ticker=query.get("ticker"),
                chunks=chunks,
            )
        )
    return [chunk.chunk_id for chunk in select_comparative_chunks(branches)]


def _branch_rows(case_payload: dict[str, Any], kept_ids: set[str]) -> list[dict[str, Any]]:
    rows = []
    for query_entry in case_payload.get("queries", []):
        query = query_entry.get("query", {})
        branch_ids = _unique_ids(query_entry.get("chunks", []))
        ticker = query.get("ticker")
        branch_text = " ".join(
            chunk.get("text", "")
            for chunk in query_entry.get("chunks", [])
            if chunk.get("chunk_id") in kept_ids
        )
        terms = branch_evidence_terms(case_payload["question"], ticker)
        coverage = _term_coverage(terms, branch_text)
        rows.append(
            {
                "ticker": ticker,
                "available_chunk_ids": branch_ids,
                "kept_chunk_ids": [
                    chunk_id for chunk_id in branch_ids if chunk_id in kept_ids
                ],
                "top_one_kept": not branch_ids or branch_ids[0] in kept_ids,
                "required_terms": list(terms),
                "required_term_coverage": coverage,
                "contract_passed": all(coverage.values()),
            }
        )
    return rows


def _known_finding(question: str, kept_ids: set[str]) -> dict[str, Any]:
    required_kept = REQUIRED_KEPT_CHUNKS.get(question, set())
    required_dropped = REQUIRED_DROPPED_CHUNKS.get(question, set())
    return {
        "required_kept": sorted(required_kept),
        "required_dropped": sorted(required_dropped),
        "kept_passed": required_kept.issubset(kept_ids),
        "dropped_passed": required_dropped.isdisjoint(kept_ids),
    }


def _measure_case(
    case_payload: dict[str, Any],
    required_keywords: list[str],
    encoder: Any,
) -> dict[str, Any]:
    full_rendered = build_evidence_context(case_payload)
    packed = pack_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V5,
    )
    packed_rendered = render_packed_blocks(packed)
    terms = evidence_terms(case_payload["question"], required_keywords)
    full_coverage = _term_coverage(terms, full_rendered)
    packed_coverage = _term_coverage(terms, packed_rendered)
    kept_ids = set(packed.kept_ids)
    branches = _branch_rows(case_payload, kept_ids)
    known_finding = _known_finding(case_payload["question"], kept_ids)
    runtime_ids = _runtime_selected_ids(case_payload)
    return {
        "question": case_payload["question"],
        "category": case_payload.get("category"),
        "full_chunks": len(_unique_ids([
            chunk
            for query in case_payload.get("queries", [])
            for chunk in query.get("chunks", [])
        ])),
        "packed_chunks": len(packed.kept),
        "full_tokens": len(encoder.encode(full_rendered)),
        "packed_tokens": len(encoder.encode(packed_rendered)),
        "required_terms": list(terms),
        "full_coverage": full_coverage,
        "packed_coverage": packed_coverage,
        "evidence_coverage_passed": (
            all(full_coverage.values()) and packed_coverage == full_coverage
        ),
        "source_boundaries_passed": _source_boundaries_match(
            packed_rendered, packed.kept
        ),
        "branch_rows": branches,
        "branch_coverage_passed": all(
            branch["top_one_kept"] for branch in branches
        ),
        "branch_contracts_passed": all(
            branch["contract_passed"] for branch in branches
        ),
        "known_finding": known_finding,
        "known_finding_passed": (
            known_finding["kept_passed"] and known_finding["dropped_passed"]
        ),
        "runtime_adapter_ids": runtime_ids,
        "runtime_adapter_match": runtime_ids == packed.kept_ids,
        "kept_chunk_ids": packed.kept_ids,
    }


def run(artifact_path: Path, priority: int = 2) -> dict[str, Any]:
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
        )
        for payload in artifact.get("cases", [])
        if payload["question"] in metadata
        and metadata[payload["question"]].priority <= priority
    ]
    rows.sort(key=lambda row: row["question"])
    comparative = [row for row in rows if row["category"] == "comparative"]
    noncomparative = [row for row in rows if row["category"] != "comparative"]
    full_tokens = sum(row["full_tokens"] for row in comparative)
    packed_tokens = sum(row["packed_tokens"] for row in comparative)
    reduction = round(
        100.0 * (full_tokens - packed_tokens) / max(full_tokens, 1), 2
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_fingerprint": embedded,
        "query_shaper_fingerprint": QUERY_SHAPER_FINGERPRINT,
        "selector_fingerprint": SELECTOR_FINGERPRINT,
        "strategy": CONTEXT_STRATEGY_COMPARATIVE_V5,
        "pre_registered_gates": {
            "expected_cases": EXPECTED_CASES,
            "expected_comparative_cases": EXPECTED_COMPARATIVE_CASES,
            "minimum_comparative_token_reduction_pct": (
                MIN_COMPARATIVE_TOKEN_REDUCTION_PCT
            ),
            "production_evaluation_adapter_parity": True,
        },
        "num_cases": len(rows),
        "num_comparative_cases": len(comparative),
        "evidence_coverage_cases": sum(
            row["evidence_coverage_passed"] for row in rows
        ),
        "source_boundary_cases": sum(
            row["source_boundaries_passed"] for row in rows
        ),
        "noncomparative_byte_stable_cases": 0,
        "comparative_branch_coverage_cases": sum(
            row["branch_coverage_passed"] for row in comparative
        ),
        "comparative_branch_contract_cases": sum(
            row["branch_contracts_passed"] for row in comparative
        ),
        "known_finding_cases": sum(
            row["known_finding_passed"] for row in comparative
        ),
        "runtime_adapter_parity_cases": sum(
            row["runtime_adapter_match"] for row in comparative
        ),
        "comparative_tokens_full": full_tokens,
        "comparative_tokens_packed": packed_tokens,
        "comparative_token_reduction_pct": reduction,
        "cases": rows,
    }
    # Non-comparative v5 is an explicit identity transformation. Verify the
    # exact bytes here instead of using token equality as a proxy.
    noncomparative_stable = 0
    payload_by_question = {
        payload["question"]: payload for payload in artifact.get("cases", [])
    }
    for row in noncomparative:
        payload = payload_by_question[row["question"]]
        noncomparative_stable += (
            build_evidence_context(payload)
            == render_packed_blocks(
                pack_case_context(
                    payload,
                    required_keywords=metadata[row["question"]].required_keywords,
                    strategy=CONTEXT_STRATEGY_COMPARATIVE_V5,
                )
            )
        )
    report["noncomparative_byte_stable_cases"] = noncomparative_stable
    report["passed"] = (
        report["num_cases"] == EXPECTED_CASES
        and report["num_comparative_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["evidence_coverage_cases"] == EXPECTED_CASES
        and report["source_boundary_cases"] == EXPECTED_CASES
        and report["noncomparative_byte_stable_cases"]
        == EXPECTED_CASES - EXPECTED_COMPARATIVE_CASES
        and report["comparative_branch_coverage_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and report["comparative_branch_contract_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and report["known_finding_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["runtime_adapter_parity_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and reduction >= MIN_COMPARATIVE_TOKEN_REDUCTION_PCT
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--artifact", type=Path, default=Path("data/eval_artifacts/phase1_priority2.json")
    )
    parser.add_argument("--priority", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run(args.artifact, args.priority)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
