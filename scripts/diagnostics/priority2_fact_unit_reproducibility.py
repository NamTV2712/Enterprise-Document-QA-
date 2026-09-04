"""Verify two provider-only unit-preservation sentinel replicates offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if len(reports) != 2:
        raise ValueError("Exactly two replicate reports are required")
    replicate_ids = [report.get("replicate_id") for report in reports]
    bindings = [
        tuple(report.get("checkpoint_provenance", {}).get("generation_binding_values", []))
        for report in reports
    ]
    judge_contexts = [
        tuple(report.get("checkpoint_provenance", {}).get("judge_context_fingerprint_values", []))
        for report in reports
    ]
    candidate_aggregates = [report.get("candidate_aggregate") for report in reports]
    gates = {
        "two_complete_replicates": all(report.get("passed") is True for report in reports),
        "distinct_replicate_ids": len(set(replicate_ids)) == 2,
        "same_artifact": len({report.get("expected_artifact_fingerprint") for report in reports}) == 1,
        "provider_only_profile": all(
            report.get("deterministic_fact_renderer") is False for report in reports
        ),
        "same_generation_binding": len(set(bindings)) == 1 and len(bindings[0]) == 1,
        "same_judge_context_fingerprint": (
            len(set(judge_contexts)) == 1 and len(judge_contexts[0]) == 1
        ),
        "identical_candidate_aggregates": candidate_aggregates[0] == candidate_aggregates[1],
    }
    return {
        "schema_version": 1,
        "audit": "priority2_fact_unit_provider_only_reproducibility_v1",
        "provider_calls": 0,
        "mutated_inputs": False,
        "replicate_ids": replicate_ids,
        "candidate_artifact_fingerprints": [
            report.get("expected_artifact_fingerprint") for report in reports
        ],
        "generation_bindings": [list(value) for value in bindings],
        "judge_context_fingerprints": [list(value) for value in judge_contexts],
        "candidate_aggregates": candidate_aggregates,
        "gates": gates,
        "passed": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", type=Path, nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [
        json.loads(path.read_text(encoding="utf-8")) for path in args.reports
    ]
    result = build_report(reports)
    result["input_sha256"] = {str(path): _sha256(path) for path in args.reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
