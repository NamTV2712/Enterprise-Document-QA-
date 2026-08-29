"""Pre-registered offline gate for comparative context packing v3.

V3 changes only comparative cases. It keeps two leading chunks per planned
branch, all structured promotions, and every keyword/fact donor required by
the shared evidence contract. The report is deterministic and provider-free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import tiktoken

from src.evaluation.context_packing import (
    COMPARATIVE_BRANCH_TARGET,
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    pack_case_context,
    render_packed_blocks,
)
from src.evaluation.evidence_contracts import evidence_terms
from src.evaluation.generation_checkpoint import build_evidence_context
from src.evaluation.test_set import TEST_SET


EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:9869912195606125b0a7efe56f091662fd50d48e08c92141415c1a174ffd0c98"
)
EXPECTED_CASES = 30
EXPECTED_COMPARATIVE_CASES = 6
MIN_COMPARATIVE_TOKEN_REDUCTION_PCT = 25.0

_SOURCE_PATTERN = re.compile(
    r"(?ms)^\[Source (?P<number>\d+)\] (?P<citation>[^\n]*)\n"
    r"(?P<text>.*?)(?=^\[Source \d+\] |\Z)"
)


def _compact(text: str) -> str:
    return "".join(text.split()).casefold()


def _term_coverage(terms: tuple[str, ...], rendered: str) -> dict[str, bool]:
    compact = _compact(rendered)
    return {term: _compact(term) in compact for term in terms}


def _source_boundaries_match(rendered: str, kept: list[dict]) -> bool:
    matches = list(_SOURCE_PATTERN.finditer(rendered))
    if len(matches) != len(kept):
        return False
    for index, (match, entry) in enumerate(zip(matches, kept, strict=True), 1):
        if int(match.group("number")) != index:
            return False
        if match.group("citation") != entry.get("citation", ""):
            return False
        if match.group("text").rstrip() != entry.get("text", "").rstrip():
            return False
    return True


def _branch_coverage(case_payload: dict, kept_ids: set[str]) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = []
    for query_entry in case_payload.get("queries", []):
        query = query_entry.get("query", {})
        branch_ids = list(
            dict.fromkeys(
                chunk.get("chunk_id") for chunk in query_entry.get("chunks", [])
            )
        )
        required = min(COMPARATIVE_BRANCH_TARGET, len(branch_ids))
        kept = [chunk_id for chunk_id in branch_ids if chunk_id in kept_ids]
        branches.append(
            {
                "effective_query": query.get("effective_query"),
                "ticker": query.get("ticker"),
                "available_chunks": len(branch_ids),
                "required_chunks": required,
                "kept_chunks": len(kept),
                "kept_chunk_ids": kept,
                "coverage_passed": len(kept) >= required,
            }
        )
    return branches


def _measure_case(case_payload: dict, required_keywords: list[str], encoder) -> dict:
    full_rendered = build_evidence_context(case_payload)
    packed = pack_case_context(
        case_payload,
        required_keywords=required_keywords,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V3,
    )
    packed_rendered = render_packed_blocks(packed)
    terms = evidence_terms(case_payload["question"], required_keywords)
    full_coverage = _term_coverage(terms, full_rendered)
    packed_coverage = _term_coverage(terms, packed_rendered)
    full_tokens = len(encoder.encode(full_rendered))
    packed_tokens = len(encoder.encode(packed_rendered))
    branches = _branch_coverage(case_payload, set(packed.kept_ids))
    category = case_payload.get("category")
    return {
        "question": case_payload["question"],
        "category": category,
        "full_chunks": len({
            chunk.get("chunk_id")
            for query in case_payload.get("queries", [])
            for chunk in query.get("chunks", [])
        }),
        "packed_chunks": len(packed.kept),
        "full_tokens": full_tokens,
        "packed_tokens": packed_tokens,
        "token_reduction_pct": round(
            100.0 * (full_tokens - packed_tokens) / max(full_tokens, 1), 2
        ),
        "required_terms": list(terms),
        "full_coverage": full_coverage,
        "packed_coverage": packed_coverage,
        "evidence_coverage_passed": (
            all(full_coverage.values()) and packed_coverage == full_coverage
        ),
        "source_boundaries_passed": _source_boundaries_match(
            packed_rendered, packed.kept
        ),
        "noncomparative_byte_stable": (
            packed_rendered == full_rendered if category != "comparative" else None
        ),
        "branches": branches if category == "comparative" else [],
        "branch_coverage_passed": (
            all(branch["coverage_passed"] for branch in branches)
            if category == "comparative"
            else True
        ),
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

    meta_by_question = {case.question: case for case in TEST_SET}
    encoder = tiktoken.get_encoding("cl100k_base")
    rows = [
        _measure_case(
            case_payload,
            meta_by_question[case_payload["question"]].required_keywords,
            encoder,
        )
        for case_payload in artifact.get("cases", [])
        if case_payload["question"] in meta_by_question
        and meta_by_question[case_payload["question"]].priority <= priority
    ]
    rows.sort(key=lambda row: row["question"])
    comparative = [row for row in rows if row["category"] == "comparative"]
    noncomparative = [row for row in rows if row["category"] != "comparative"]
    comparative_full_tokens = sum(row["full_tokens"] for row in comparative)
    comparative_packed_tokens = sum(row["packed_tokens"] for row in comparative)
    reduction = round(
        100.0
        * (comparative_full_tokens - comparative_packed_tokens)
        / max(comparative_full_tokens, 1),
        2,
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_fingerprint": embedded,
        "strategy": CONTEXT_STRATEGY_COMPARATIVE_V3,
        "pre_registered_gates": {
            "expected_cases": EXPECTED_CASES,
            "expected_comparative_cases": EXPECTED_COMPARATIVE_CASES,
            "branch_target": COMPARATIVE_BRANCH_TARGET,
            "minimum_comparative_token_reduction_pct": (
                MIN_COMPARATIVE_TOKEN_REDUCTION_PCT
            ),
        },
        "num_cases": len(rows),
        "num_comparative_cases": len(comparative),
        "evidence_coverage_cases": sum(
            row["evidence_coverage_passed"] for row in rows
        ),
        "source_boundary_cases": sum(
            row["source_boundaries_passed"] for row in rows
        ),
        "noncomparative_byte_stable_cases": sum(
            row["noncomparative_byte_stable"] for row in noncomparative
        ),
        "comparative_branch_coverage_cases": sum(
            row["branch_coverage_passed"] for row in comparative
        ),
        "comparative_tokens_full": comparative_full_tokens,
        "comparative_tokens_packed": comparative_packed_tokens,
        "comparative_token_reduction_pct": reduction,
        "cases": rows,
    }
    report["passed"] = (
        report["num_cases"] == EXPECTED_CASES
        and report["num_comparative_cases"] == EXPECTED_COMPARATIVE_CASES
        and report["evidence_coverage_cases"] == EXPECTED_CASES
        and report["source_boundary_cases"] == EXPECTED_CASES
        and report["noncomparative_byte_stable_cases"]
        == EXPECTED_CASES - EXPECTED_COMPARATIVE_CASES
        and report["comparative_branch_coverage_cases"]
        == EXPECTED_COMPARATIVE_CASES
        and reduction >= MIN_COMPARATIVE_TOKEN_REDUCTION_PCT
    )
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["report_fingerprint"] = (
        "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
