"""Offline gate for the composite selective_packed_v2 policy.

The policy keeps the previously admitted route-aware packing for fact_lookup,
multi_hop, and summary cases, applies the oracle-free comparative v5 selector
only to comparative cases, and leaves enumeration/out-of-corpus cases at full
evidence. This diagnostic never calls a provider or reruns retrieval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import tiktoken

from scripts.diagnostics.comparative_packing_v3 import (
    _source_boundaries_match,
    _term_coverage,
)
from scripts.diagnostics.comparative_packing_v5 import (
    _branch_rows,
    _known_finding,
    _runtime_selected_ids,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V5,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_SELECTIVE,
    CONTEXT_STRATEGY_SELECTIVE_V2,
    collect_entries,
    effective_case_context_strategy,
    pack_case_context,
    render_case_context,
)
from src.evaluation.evidence_contracts import evidence_terms
from src.evaluation.generation_checkpoint import build_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.comparative_context import COMPARATIVE_SELECTOR_FINGERPRINT
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT


EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:1ad021ce72af2116f9b4f7ad780d5c6e809fd5a01e46d30d0ae4bfecd62599d9"
)
EXPECTED_CASES = 30
EXPECTED_COMPARATIVE_CASES = 6
EXPECTED_NONCOMPARATIVE_CASES = 24
MIN_TOTAL_TOKEN_REDUCTION_PCT = 25.0


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _unique_ids(entries: list[dict[str, Any]]) -> list[str | None]:
    return list(dict.fromkeys(entry.get("chunk_id") for entry in entries))


def _entries_for_strategy(
    case_payload: dict[str, Any],
    required_keywords: list[str],
    strategy: str,
) -> list[dict[str, Any]]:
    concrete = effective_case_context_strategy(
        strategy, case_payload.get("category", "")
    )
    if concrete == CONTEXT_STRATEGY_FULL_EVIDENCE:
        return collect_entries(case_payload)
    return pack_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=concrete,
    ).kept


def _measure_case(
    case_payload: dict[str, Any],
    required_keywords: list[str],
    encoder: Any,
) -> dict[str, Any]:
    full = build_evidence_context(case_payload)
    baseline = render_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE,
    )
    candidate = render_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
    )
    v5 = render_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V5,
    )
    candidate_entries = _entries_for_strategy(
        case_payload, required_keywords, CONTEXT_STRATEGY_SELECTIVE_V2
    )
    terms = evidence_terms(case_payload["question"], required_keywords)
    full_coverage = _term_coverage(terms, full)
    candidate_coverage = _term_coverage(terms, candidate)
    category = case_payload.get("category")
    row: dict[str, Any] = {
        "question": case_payload["question"],
        "category": category,
        "full_tokens": len(encoder.encode(full)),
        "baseline_tokens": len(encoder.encode(baseline)),
        "candidate_tokens": len(encoder.encode(candidate)),
        "baseline_chunk_ids": _unique_ids(
            _entries_for_strategy(
                case_payload, required_keywords, CONTEXT_STRATEGY_SELECTIVE
            )
        ),
        "candidate_chunk_ids": _unique_ids(candidate_entries),
        "full_coverage": full_coverage,
        "candidate_coverage": candidate_coverage,
        "candidate_evidence_coverage_passed": (
            candidate_coverage == full_coverage
        ),
        "candidate_source_boundaries_passed": _source_boundaries_match(
            candidate, candidate_entries
        ),
        "candidate_strategy": effective_case_context_strategy(
            CONTEXT_STRATEGY_SELECTIVE_V2, category or ""
        ),
        "noncomparative_byte_stable": (
            category == "comparative" or candidate == baseline
        ),
        "comparative_v5_byte_stable": (
            category != "comparative" or candidate == v5
        ),
    }
    if category == "comparative":
        kept_ids = set(row["candidate_chunk_ids"])
        branches = _branch_rows(case_payload, kept_ids)
        known_finding = _known_finding(case_payload["question"], kept_ids)
        runtime_ids = _runtime_selected_ids(case_payload)
        row.update(
            {
                "branch_rows": branches,
                "branch_coverage_passed": all(
                    branch["top_one_kept"] for branch in branches
                ),
                "branch_contracts_passed": all(
                    branch["contract_passed"] for branch in branches
                ),
                "known_finding": known_finding,
                "known_finding_passed": (
                    known_finding["kept_passed"]
                    and known_finding["dropped_passed"]
                ),
                "runtime_selector_ids": runtime_ids,
                "runtime_selector_parity": (
                    runtime_ids == row["candidate_chunk_ids"]
                ),
            }
        )
    return row


def run(artifact_path: Path, priority: int = 2) -> dict[str, Any]:
    before_sha = _file_sha256(artifact_path)
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
    totals = {
        "full": sum(row["full_tokens"] for row in rows),
        "baseline": sum(row["baseline_tokens"] for row in rows),
        "candidate": sum(row["candidate_tokens"] for row in rows),
    }
    reduction_vs_baseline = round(
        100.0 * (totals["baseline"] - totals["candidate"])
        / max(totals["baseline"], 1),
        2,
    )
    reduction_vs_full = round(
        100.0 * (totals["full"] - totals["candidate"])
        / max(totals["full"], 1),
        2,
    )
    after_sha = _file_sha256(artifact_path)

    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_fingerprint": embedded,
        "artifact_file_sha256_before": before_sha,
        "artifact_file_sha256_after": after_sha,
        "input_immutable": before_sha == after_sha,
        "query_shaper_fingerprint": QUERY_SHAPER_FINGERPRINT,
        "lexical_ladder_fingerprint": LEXICAL_LADDER_FINGERPRINT,
        "comparative_selector_fingerprint": COMPARATIVE_SELECTOR_FINGERPRINT,
        "baseline_strategy": CONTEXT_STRATEGY_SELECTIVE,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "effective_policy": {
            "fact_lookup": "route_aware_v2",
            "multi_hop": "route_aware_v2",
            "summary": "route_aware_v2",
            "comparative": CONTEXT_STRATEGY_COMPARATIVE_V5,
            "enumeration": CONTEXT_STRATEGY_FULL_EVIDENCE,
            "out_of_corpus": CONTEXT_STRATEGY_FULL_EVIDENCE,
        },
        "pre_registered_gates": {
            "expected_cases": EXPECTED_CASES,
            "expected_comparative_cases": EXPECTED_COMPARATIVE_CASES,
            "expected_noncomparative_cases": EXPECTED_NONCOMPARATIVE_CASES,
            "minimum_total_token_reduction_vs_selective_pct": (
                MIN_TOTAL_TOKEN_REDUCTION_PCT
            ),
            "noncomparative_byte_identity": True,
            "comparative_v5_byte_identity": True,
            "production_evaluation_adapter_parity": True,
        },
        "num_cases": len(rows),
        "num_comparative_cases": len(comparative),
        "num_noncomparative_cases": len(noncomparative),
        "evidence_coverage_cases": sum(
            row["candidate_evidence_coverage_passed"] for row in rows
        ),
        "source_boundary_cases": sum(
            row["candidate_source_boundaries_passed"] for row in rows
        ),
        "noncomparative_byte_stable_cases": sum(
            row["noncomparative_byte_stable"] for row in noncomparative
        ),
        "comparative_v5_byte_stable_cases": sum(
            row["comparative_v5_byte_stable"] for row in comparative
        ),
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
            row["runtime_selector_parity"] for row in comparative
        ),
        "token_totals": totals,
        "token_reduction_vs_selective_pct": reduction_vs_baseline,
        "token_reduction_vs_full_pct": reduction_vs_full,
        "cases": rows,
    }
    report["passed"] = (
        report["input_immutable"]
        and report["num_cases"] == EXPECTED_CASES
        and report["num_comparative_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["num_noncomparative_cases"] == EXPECTED_NONCOMPARATIVE_CASES
        and report["evidence_coverage_cases"] == EXPECTED_CASES
        and report["source_boundary_cases"] == EXPECTED_CASES
        and report["noncomparative_byte_stable_cases"]
        == EXPECTED_NONCOMPARATIVE_CASES
        and report["comparative_v5_byte_stable_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and report["comparative_branch_coverage_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and report["comparative_branch_contract_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and report["known_finding_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["runtime_adapter_parity_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and reduction_vs_baseline >= MIN_TOTAL_TOKEN_REDUCTION_PCT
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
