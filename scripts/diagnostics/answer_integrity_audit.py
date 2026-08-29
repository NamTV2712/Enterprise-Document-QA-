"""Audit frozen Phase 2 answers without making network/provider calls.

Run as ``python -m scripts.diagnostics.answer_integrity_audit`` from the
repository root.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.evaluation.answer_contract import audit_answer, render_source_texts


def run(results_path: Path, artifact_path: Path) -> dict:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    by_question = {case["question"]: case for case in artifact["cases"]}
    rows = []
    for case in results.get("cases", []):
        question = case["question"]
        source_texts = render_source_texts(by_question[question])
        audit = audit_answer(case.get("answer") or "", source_texts)
        rows.append({"question": question, **audit.to_dict()})

    rows.sort(key=lambda row: row["question"])
    non_fallback = [row for row in rows if not row["fallback_answer"]]
    return {
        "schema_version": 1,
        "results_path": str(results_path),
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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.results, args.artifact)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
