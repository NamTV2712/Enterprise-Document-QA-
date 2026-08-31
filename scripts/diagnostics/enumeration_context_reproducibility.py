"""Require two passing enumeration-context sentinel replicates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MIN_REPLICATES = 2
REQUIRED_PASS_RATE = 1.0
EXPECTED_AUDIT = "enumeration_context_sentinel_v1"


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _provenance_complete(report: dict[str, Any]) -> bool:
    questions = set(report.get("sentinel_questions") or [])
    provenance = report.get("replicate_provenance") or {}
    answer_hashes = provenance.get("generation_answer_hashes") or {}
    generation_bindings = provenance.get("generation_bindings") or {}
    judge_bindings = provenance.get("judge_bindings") or {}
    return (
        bool(questions)
        and set(answer_hashes) == questions
        and set(generation_bindings) == questions
        and set(judge_bindings) == questions
        and all(
            isinstance(value, str) and value.startswith("sha256:")
            for value in answer_hashes.values()
        )
        and all(isinstance(value, str) and value for value in generation_bindings.values())
        and all(isinstance(value, str) and value for value in judge_bindings.values())
    )


def build_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    replicate_ids = [report.get("replicate_id") for report in reports]
    strategies = {report.get("context_strategy") for report in reports}
    artifacts = {report.get("bound_artifact_fingerprint") for report in reports}
    bindings = {report.get("binding") for report in reports}
    completions = {report.get("completion_fingerprint") for report in reports}
    question_sets = {
        frozenset(report.get("sentinel_questions") or []) for report in reports
    }
    complete = [
        bool(
            report.get("audit") == EXPECTED_AUDIT
            and report.get("provider_complete")
            and report.get("passed")
            and all((report.get("gates") or {}).values())
            and _provenance_complete(report)
        )
        for report in reports
    ]
    passed_count = sum(complete)
    pass_rate = passed_count / len(reports) if reports else 0.0
    gates = {
        "minimum_replicates": len(reports) >= MIN_REPLICATES,
        "unique_replicate_ids": len(replicate_ids) == len(set(replicate_ids))
        and all(isinstance(value, str) and value for value in replicate_ids),
        "one_candidate_strategy": len(strategies) == 1 and None not in strategies,
        "one_frozen_artifact": len(artifacts) == 1 and None not in artifacts,
        "one_generation_binding": len(bindings) == 1 and None not in bindings,
        "one_completion_fingerprint": len(completions) == 1
        and None not in completions,
        "one_sentinel_question_set": len(question_sets) == 1
        and bool(next(iter(question_sets), frozenset())),
        "complete_provenance": bool(reports)
        and all(_provenance_complete(report) for report in reports),
        "all_replicates_pass": bool(complete) and all(complete),
        "required_pass_rate": pass_rate >= REQUIRED_PASS_RATE,
    }
    return {
        "schema_version": 1,
        "audit": "enumeration_context_reproducibility",
        "pre_registered_rule": {
            "minimum_replicates": MIN_REPLICATES,
            "required_pass_rate": REQUIRED_PASS_RATE,
            "failed_replicates_are_not_averaged_away": True,
            "best_of_selection_forbidden": True,
        },
        "num_replicates": len(reports),
        "replicate_ids": replicate_ids,
        "candidate_strategy": next(iter(strategies), None),
        "candidate_bindings": sorted(bindings - {None}),
        "completion_fingerprints": sorted(completions - {None}),
        "replicate_pass_count": passed_count,
        "replicate_pass_rate": round(pass_rate, 4),
        "replicates": [
            {
                "replicate_id": replicate_id,
                "path": report.get("report_path"),
                "report_sha256": report.get("report_sha256"),
                "passed": bool(passed),
                "candidate_aggregate": report.get("candidate_aggregate"),
            }
            for replicate_id, passed, report in zip(
                replicate_ids, complete, reports
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "passed": report["passed"],
        "replicate_pass_count": report["replicate_pass_count"],
        "replicate_pass_rate": report["replicate_pass_rate"],
        "gates": report["gates"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
