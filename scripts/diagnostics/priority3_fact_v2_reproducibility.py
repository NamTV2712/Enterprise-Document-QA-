"""Verify the two independent P3 Fact Evidence Sufficiency v2 sentinels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.generation.fact_context import FACT_CONTEXT_SELECTOR_FINGERPRINT_V2


DEFAULT_REPORTS = (
    Path("data/diagnostics/priority3_fact_v2_sentinel_r1.json"),
    Path("data/diagnostics/priority3_fact_v2_sentinel_r2.json"),
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/priority3_fact_v2_reproducibility.json"
)
EXPECTED_STRATEGY = "selective_packed_v7_fact_generalization_candidate"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _all_true(mapping: Any) -> bool:
    return isinstance(mapping, dict) and bool(mapping) and all(
        value is True for value in mapping.values()
    )


def _checkpoint_hashes_match(report: dict[str, Any]) -> bool:
    provenance = report.get("checkpoint_provenance")
    if not isinstance(provenance, dict):
        return False
    for path_key, hash_key in (
        ("generation_checkpoint", "generation_checkpoint_sha256"),
        ("judge_checkpoint", "judge_checkpoint_sha256"),
    ):
        path_value = provenance.get(path_key)
        expected = provenance.get(hash_key)
        if not isinstance(path_value, str) or not isinstance(expected, str):
            return False
        path = Path(path_value)
        if not path.exists() or _sha256(path) != expected:
            return False
    return True


def _selector_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("selector_rows") or {}
    return {
        question: {
            key: rows.get(question, {}).get(key)
            for key in ("selector_tier", "selected_chunk_ids", "source_count", "context_sha256", "safe")
        }
        for question in report.get("sentinel_questions", [])
    }


def build_report(reports: list[dict[str, Any]], paths: list[Path]) -> dict[str, Any]:
    replicate_ids = [report.get("replicate_id") for report in reports]
    bindings = {report.get("binding") for report in reports}
    artifact_fingerprints = {
        report.get("bound_artifact_fingerprint") for report in reports
    }
    selector_fingerprints = {
        report.get("selector_fingerprint") for report in reports
    }
    questions = [report.get("sentinel_questions") for report in reports]
    same_selector = (
        len(reports) == 2
        and questions[0] == questions[1]
        and _selector_snapshot(reports[0]) == _selector_snapshot(reports[1])
    )
    provenance_complete = len(reports) == 2 and all(
        _checkpoint_hashes_match(report)
        and isinstance(report.get("checkpoint_provenance"), dict)
        and len(
            report["checkpoint_provenance"].get("generation_binding_values", [])
        )
        == 1
        and len(
            report["checkpoint_provenance"].get("judge_context_fingerprint_values", [])
        )
        == 1
        for report in reports
    )
    all_replicates_pass = len(reports) == 2 and all(
        report.get("passed") is True
        and report.get("official") is False
        and report.get("provider_complete") is True
        and report.get("context_strategy") == EXPECTED_STRATEGY
        and report.get("selector_fingerprint") == FACT_CONTEXT_SELECTOR_FINGERPRINT_V2
        and _all_true(report.get("gates"))
        for report in reports
    )
    gates = {
        "exactly_two_replicates": len(reports) == 2,
        "unique_replicate_ids": len(replicate_ids) == len(set(replicate_ids))
        and all(isinstance(value, str) and value for value in replicate_ids),
        "all_replicates_pass": all_replicates_pass,
        "one_strategy": {
            report.get("context_strategy") for report in reports
        }
        == {EXPECTED_STRATEGY},
        "one_binding": len(bindings) == 1 and None not in bindings,
        "one_upstream_artifact": len(artifact_fingerprints) == 1
        and None not in artifact_fingerprints,
        "one_selector_fingerprint": selector_fingerprints
        == {FACT_CONTEXT_SELECTOR_FINGERPRINT_V2},
        "same_deterministic_selector_context": same_selector,
        "complete_checkpoint_provenance": provenance_complete,
        "no_best_of_selection": True,
    }
    return {
        "schema_version": 1,
        "audit": "priority3_fact_v2_reproducibility",
        "official": False,
        "candidate_strategy": EXPECTED_STRATEGY,
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
        "report_paths": [str(path) for path in paths],
        "report_sha256": [_sha256(path) for path in paths],
        "replicate_ids": replicate_ids,
        "generation_bindings": [report.get("binding") for report in reports],
        "pre_registered_rule": {
            "minimum_replicates": 2,
            "required_pass_rate": 1.0,
            "best_of_selection_forbidden": True,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    report_paths: tuple[Path, ...] = DEFAULT_REPORTS,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    reports = [
        json.loads(path.read_text(encoding="utf-8")) for path in report_paths
    ]
    report = build_report(reports, list(report_paths))
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r1", type=Path, default=DEFAULT_REPORTS[0])
    parser.add_argument("--r2", type=Path, default=DEFAULT_REPORTS[1])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run((args.r1, args.r2), args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
