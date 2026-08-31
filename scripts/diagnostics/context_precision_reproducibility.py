"""Check independent sentinel replicates before authorizing a full replay.

The protocol is deliberately conservative: every replicate must be complete,
deterministically grounded, and non-regressing against the protected v2
reference. It never selects the best replicate and never averages away a
failed run. A passing report is therefore an authorization prerequisite for a
future candidate N=30 run, not an evaluation score itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_context_precision_sentinel import SENTINEL_QUESTIONS

MIN_REPLICATES = 2
REQUIRED_PASS_RATE = 1.0


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _provenance_complete(report: dict[str, Any]) -> bool:
    provenance = report.get("replicate_provenance") or {}
    answer_hashes = provenance.get("generation_answer_hashes") or {}
    generation_bindings = provenance.get("generation_bindings") or {}
    judge_bindings = provenance.get("judge_bindings") or {}
    questions = set(SENTINEL_QUESTIONS)
    return (
        set(answer_hashes) == questions
        and set(generation_bindings) == questions
        and set(judge_bindings) == questions
        and all(
            isinstance(value, str) and value.startswith("sha256:")
            for value in answer_hashes.values()
        )
        and all(
            isinstance(value, str) and value.startswith("sha256:")
            for value in generation_bindings.values()
        )
        and all(
            isinstance(value, str) and value.startswith("sha256:")
            for value in judge_bindings.values()
        )
    )


def build_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the pre-registered all-replicates reproducibility gate."""
    strategy_values = {report.get("context_strategy") for report in reports}
    artifact_values = {
        report.get("bound_artifact_fingerprint") for report in reports
    }
    binding_values = {report.get("binding") for report in reports}
    replicate_ids = [
        report.get("replicate_id")
        or (report.get("replicate_provenance") or {}).get("replicate_id")
        for report in reports
    ]
    unique_replicate_ids = (
        len(replicate_ids) == len(set(replicate_ids))
        and all(isinstance(value, str) and value for value in replicate_ids)
    )

    complete_rows = [
        bool(
            report.get("provider_complete")
            and report.get("gates", {}).get("provider_complete")
            and report.get("gates", {}).get("deterministic_passed")
            and report.get("gates", {}).get("score_regression_passed")
            and _provenance_complete(report)
        )
        for report in reports
    ]
    passed_count = sum(complete_rows)
    pass_rate = passed_count / len(reports) if reports else 0.0
    gates = {
        "minimum_replicates": len(reports) >= MIN_REPLICATES,
        "unique_replicate_ids": unique_replicate_ids,
        "one_candidate_strategy": len(strategy_values) == 1
        and None not in strategy_values,
        "one_frozen_artifact": len(artifact_values) == 1
        and None not in artifact_values,
        "one_generation_binding": len(binding_values) == 1
        and None not in binding_values,
        "complete_provenance": all(
            _provenance_complete(report) for report in reports
        ) and bool(reports),
        "all_replicates_pass": bool(complete_rows) and all(complete_rows),
        "required_pass_rate": pass_rate >= REQUIRED_PASS_RATE,
    }
    return {
        "schema_version": 1,
        "audit": "context_precision_reproducibility",
        "pre_registered_rule": {
            "minimum_replicates": MIN_REPLICATES,
            "required_pass_rate": REQUIRED_PASS_RATE,
            "failed_replicates_are_not_averaged_away": True,
            "best_of_selection_forbidden": True,
        },
        "num_replicates": len(reports),
        "replicate_ids": replicate_ids,
        "candidate_strategy": next(iter(strategy_values), None),
        "candidate_bindings": sorted(binding_values - {None}),
        "replicate_pass_count": passed_count,
        "replicate_pass_rate": round(pass_rate, 4),
        "replicates": [
            {
                "replicate_id": replicate_id,
                "path": report.get("report_path"),
                "report_sha256": report.get("report_sha256"),
                "passed": bool(row),
                "candidate_aggregate": report.get("candidate_aggregate"),
                "generation_answer_hashes": (
                    report.get("replicate_provenance", {})
                    .get("generation_answer_hashes", {})
                ),
                "generation_bindings": (
                    report.get("replicate_provenance", {})
                    .get("generation_bindings", {})
                ),
                "judge_bindings": (
                    report.get("replicate_provenance", {})
                    .get("judge_bindings", {})
                ),
            }
            for replicate_id, row, report in zip(
                replicate_ids, complete_rows, reports
            )
        ],
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(paths: list[Path]) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        report["report_path"] = str(path)
        report["report_sha256"] = _file_sha256(path)
        reports.append(report)
    return build_report(reports)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run(args.reports)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
