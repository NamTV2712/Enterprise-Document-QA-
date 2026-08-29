"""Audit frozen Phase 2 answers without making network/provider calls.

Run as ``python -m scripts.diagnostics.answer_integrity_audit`` from the
repository root.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.evaluation.answer_contract import audit_answer, render_source_texts
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    CONTEXT_STRATEGY_COMPARATIVE_V5,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    CONTEXT_STRATEGY_SELECTIVE,
    CONTEXT_STRATEGY_SELECTIVE_V2,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET


def run(
    results_path: Path,
    artifact_path: Path,
    context_strategy: str = CONTEXT_STRATEGY_FULL_EVIDENCE,
) -> dict:
    """Audit answers against the exact evidence rendering used by the run."""
    results = json.loads(results_path.read_text(encoding="utf-8"))
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    by_question = {case["question"]: case for case in artifact["cases"]}
    metadata = {case.question: case for case in TEST_SET}
    rows = []
    for case in results.get("cases", []):
        question = case["question"]
        payload = by_question[question]
        if context_strategy == CONTEXT_STRATEGY_FULL_EVIDENCE:
            source_texts = render_source_texts(payload)
        else:
            rendered = render_case_context(
                payload,
                required_keywords=metadata[question].required_keywords,
                strategy=context_strategy,
            )
            source_texts = [
                block["text"]
                for block in parse_evidence_context(rendered)
            ]
        audit = audit_answer(case.get("answer") or "", source_texts)
        rows.append({"question": question, **audit.to_dict()})

    rows.sort(key=lambda row: row["question"])
    non_fallback = [row for row in rows if not row["fallback_answer"]]
    return {
        "schema_version": 2,
        "results_path": str(results_path),
        "context_strategy": context_strategy,
        "num_cases": len(rows),
        "num_fallback": sum(row["fallback_answer"] for row in rows),
        "num_uncited_non_fallback": sum(row["uncited_answer"] for row in non_fallback),
        "num_malformed_line_citation_cases": sum(
            row["malformed_line_citations"] > 0 for row in rows
        ),
        "num_out_of_range_citation_cases": sum(
            bool(row["out_of_range_citations"]) for row in rows
        ),
        "num_numeric_review_cases": sum(
            bool(row["unsupported_numeric_claims"]) for row in rows
        ),
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument(
        "--context-strategy",
        choices=[
            CONTEXT_STRATEGY_FULL_EVIDENCE,
            CONTEXT_STRATEGY_ROUTE_AWARE,
            CONTEXT_STRATEGY_SELECTIVE,
            CONTEXT_STRATEGY_COMPARATIVE_V3,
            CONTEXT_STRATEGY_COMPARATIVE_V5,
            CONTEXT_STRATEGY_SELECTIVE_V2,
        ],
        default=CONTEXT_STRATEGY_FULL_EVIDENCE,
        help=(
            "Evidence policy used to number [Source N] blocks. Use the same "
            "strategy as the Phase 2 run; the default preserves the legacy "
            "full-evidence audit."
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.results, args.artifact, args.context_strategy)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
