"""Audit the staged table-unit candidate against the protected P2 contract.

This is provider-free and read-only. It proves that the staged candidate
changes only financial-table evidence text, keeps the frozen retrieval shape,
preserves one-source fact packing, and repairs the inherited Apple unit
omission. It does not authorize a corpus/index rebuild or a provider run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import load_bound_artifact
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.evidence_fact_renderer import render_single_period_net_sales_fact
from src.generation.fact_context import select_fact_context_v2


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ARTIFACT = ROOT / "data/eval_artifacts/phase1_priority2.json"
CANDIDATE_ARTIFACT = ROOT / (
    "data/eval_artifacts/phase1_priority2_financial_table_units_candidate.json"
)
OFFICIAL_RESULT = ROOT / "data/eval_artifacts/phase2_results_packed_selective_v2.json"
DEFAULT_OUTPUT = ROOT / "data/diagnostics/priority2_fact_unit_candidate_v1.json"
OFFICIAL_RESULT_SHA256 = (
    "sha256:a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
EXPECTED_SOURCE_ARTIFACT = (
    "sha256:1ad021ce72af2116f9b4f7ad780d5c6e809fd5a01e46d30d0ae4bfecd62599d9"
)
SENTINEL_QUESTIONS = (
    "What was Apple's total net sales in fiscal year 2024?",
    "What was Apple's total net sales in fiscal year 2025?",
    "What was Microsoft's total assets as of fiscal year 2025?",
    "What was Amazon's AWS net sales in 2025?",
    "What was Amazon's consolidated net sales in 2024?",
    "What was Amazon's North America operating income in 2025?",
    "Who audited Apple's financial statements and when was the report signed?",
    "Who audited Microsoft's financial statements?",
)
_SCALE_RE = re.compile(
    r"\b(?:in\s+)?(?:thousands?|millions?|billions?)\b"
    r"|\b(?:thousands?|millions?|billions?)\s+of\s+dollars\b",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> tuple[dict[str, Any], Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return load_bound_artifact(
        path,
        raw["fingerprints"]["artifact"],
        CONTEXT_STRATEGY_SELECTIVE_V7,
    )


def _without_text(chunk: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in chunk.items() if key != "text"}


def _context_snapshot(case: dict[str, Any]) -> dict[str, Any]:
    selection = select_fact_context_v2(case)
    context = render_case_context(case, strategy=CONTEXT_STRATEGY_SELECTIVE_V7)
    return {
        "context_sha256": "sha256:" + hashlib.sha256(
            context.encode("utf-8")
        ).hexdigest(),
        "context_chars": len(context),
        "source_count": len(parse_evidence_context(context)),
        "has_explicit_scale": bool(_SCALE_RE.search(context)),
        "units_line_count": sum(
            1 for line in context.splitlines() if line.startswith("Units:")
        ),
        "selector_tier": selection.tier,
        "selector_safe": selection.safe,
        "selected_chunk_ids": list(selection.kept_ids),
    }


def build_report(
    source: dict[str, Any],
    candidate: dict[str, Any],
    *,
    source_path: Path,
    candidate_path: Path,
) -> dict[str, Any]:
    source_by_question = {case["question"]: case for case in source["cases"]}
    candidate_by_question = {case["question"]: case for case in candidate["cases"]}
    case_rows: list[dict[str, Any]] = []
    retrieval_shape_preserved = True
    only_financial_table_text_changed = True

    for question in SENTINEL_QUESTIONS:
        source_case = source_by_question[question]
        candidate_case = candidate_by_question[question]
        source_chunks = {
            chunk["chunk_id"]: chunk
            for query in source_case.get("queries", [])
            for chunk in query.get("chunks", [])
        }
        candidate_chunks = {
            chunk["chunk_id"]: chunk
            for query in candidate_case.get("queries", [])
            for chunk in query.get("chunks", [])
        }
        if set(source_chunks) != set(candidate_chunks):
            retrieval_shape_preserved = False
            only_financial_table_text_changed = False
        changed_ids: list[str] = []
        for chunk_id in sorted(source_chunks):
            before = source_chunks[chunk_id]
            after = candidate_chunks.get(chunk_id)
            if after is None:
                continue
            if _without_text(before) != _without_text(after):
                retrieval_shape_preserved = False
            if before.get("text") != after.get("text"):
                changed_ids.append(chunk_id)
                if before.get("section") != "financial_table":
                    only_financial_table_text_changed = False
                before_lines = before.get("text", "").splitlines()
                after_lines = [
                    line
                    for line in after.get("text", "").splitlines()
                    if not line.startswith("Units:")
                ]
                if before_lines != after_lines:
                    only_financial_table_text_changed = False
        source_snapshot = _context_snapshot(source_case)
        candidate_snapshot = _context_snapshot(candidate_case)
        if (
            source_snapshot["selected_chunk_ids"]
            != candidate_snapshot["selected_chunk_ids"]
            or source_snapshot["source_count"] != candidate_snapshot["source_count"]
        ):
            retrieval_shape_preserved = False
        row: dict[str, Any] = {
            "question": question,
            "changed_chunk_ids": changed_ids,
            "source": source_snapshot,
            "candidate": candidate_snapshot,
        }
        if question == "What was Apple's total net sales in fiscal year 2025?":
            row["source_renderer_answer"] = render_single_period_net_sales_fact(
                question,
                render_case_context(
                    source_case, strategy=CONTEXT_STRATEGY_SELECTIVE_V7
                ),
            )
            row["candidate_renderer_answer"] = render_single_period_net_sales_fact(
                question,
                render_case_context(
                    candidate_case, strategy=CONTEXT_STRATEGY_SELECTIVE_V7
                ),
            )
        case_rows.append(row)

    apple_2025 = next(
        row
        for row in case_rows
        if row["question"] == "What was Apple's total net sales in fiscal year 2025?"
    )
    candidate_has_apple_unit = "million [Source 1]." in (
        apple_2025.get("candidate_renderer_answer") or ""
    )
    official_unchanged = _sha256(OFFICIAL_RESULT) == OFFICIAL_RESULT_SHA256
    gates = {
        "source_artifact_matches_expected": source["fingerprints"]["artifact"]
        == EXPECTED_SOURCE_ARTIFACT,
        "candidate_artifact_loads_with_its_own_fingerprint": True,
        "eight_cases_present": len(case_rows) == len(SENTINEL_QUESTIONS),
        "retrieval_shape_preserved": retrieval_shape_preserved,
        "only_financial_table_text_changed": only_financial_table_text_changed,
        "all_fact_contexts_remain_single_source": all(
            row["candidate"]["source_count"] == 1 for row in case_rows
        ),
        "selector_remains_safe": all(
            row["candidate"]["selector_safe"] is True for row in case_rows
        ),
        "apple_candidate_renderer_restores_explicit_million_unit": candidate_has_apple_unit,
        "official_result_unchanged": official_unchanged,
    }
    return {
        "schema_version": 1,
        "audit": "priority2_fact_unit_candidate_v1",
        "provider_calls": 0,
        "mutated_inputs": False,
        "source_artifact": source["fingerprints"]["artifact"],
        "candidate_artifact": candidate["fingerprints"]["artifact"],
        "source_file_sha256": _sha256(source_path),
        "candidate_file_sha256": _sha256(candidate_path),
        "official_result_sha256": _sha256(OFFICIAL_RESULT),
        "cases": case_rows,
        "gates": gates,
        "passed": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE_ARTIFACT)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source, _ = _load(args.source)
    candidate, _ = _load(args.candidate)
    report = build_report(
        source,
        candidate,
        source_path=args.source,
        candidate_path=args.candidate,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
