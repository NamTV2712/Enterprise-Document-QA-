"""Verify the two priority-2 Fact Evidence Sufficiency v2 compatibility replicates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_priority2_fact_v2_compatibility_sentinel import (
    EXPECTED_ARTIFACT_FINGERPRINT,
    SENTINEL_QUESTIONS,
)
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V7
from src.generation.fact_context import FACT_CONTEXT_SELECTOR_FINGERPRINT_V2


DEFAULT_REPORTS = (
    Path("data/diagnostics/priority2_fact_v2_compatibility_sentinel_r1.json"),
    Path("data/diagnostics/priority2_fact_v2_compatibility_sentinel_r2.json"),
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/priority2_fact_v2_compatibility_reproducibility.json"
)


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _all_true(value: Any) -> bool:
    return isinstance(value, dict) and bool(value) and all(item is True for item in value.values())


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
        if not path.exists() or _file_sha256(path) != expected:
            return False
    return True


def build_report(reports: list[dict[str, Any]], report_paths: list[Path]) -> dict[str, Any]:
    replicate_ids = [report.get("replicate_id") for report in reports]
    selector_rows = [report.get("selector_rows") or {} for report in reports]
    same_selector_context = False
    if len(selector_rows) == 2:
        same_selector_context = all(
            selector_rows[0].get(question) == selector_rows[1].get(question)
            for question in SENTINEL_QUESTIONS
        )
    provenance_complete = all(
        isinstance(report.get("checkpoint_provenance"), dict)
        and _checkpoint_hashes_match(report)
        and len(report["checkpoint_provenance"].get("generation_binding_values", [])) == 1
        and len(report["checkpoint_provenance"].get("judge_binding_values", [])) == len(SENTINEL_QUESTIONS)
        and len(report["checkpoint_provenance"].get("judge_context_fingerprint_values", [])) == 1
        and len(report["sentinel_questions"]) == len(SENTINEL_QUESTIONS)
        for report in reports
    )
    all_replicates_pass = len(reports) == 2 and all(
        report.get("passed") is True
        and report.get("official") is False
        and report.get("context_strategy") == CONTEXT_STRATEGY_SELECTIVE_V7
        and report.get("expected_artifact_fingerprint") == EXPECTED_ARTIFACT_FINGERPRINT
        and tuple(report.get("sentinel_questions") or ()) == SENTINEL_QUESTIONS
        and _all_true(report.get("gates"))
        for report in reports
    )
    bindings = {
        tuple(report.get("checkpoint_provenance", {}).get("generation_binding_values", []))
        for report in reports
    }
    gates = {
        "exactly_two_replicates": len(reports) == 2,
        "unique_replicate_ids": len(replicate_ids) == len(set(replicate_ids))
        and all(isinstance(value, str) and value for value in replicate_ids),
        "all_replicates_pass": all_replicates_pass,
        "one_strategy": {report.get("context_strategy") for report in reports}
        == {CONTEXT_STRATEGY_SELECTIVE_V7},
        "one_upstream_artifact": {
            report.get("expected_artifact_fingerprint") for report in reports
        }
        == {EXPECTED_ARTIFACT_FINGERPRINT},
        "one_selector_fingerprint": {
            report.get("selector_fingerprint") for report in reports
        }
        == {FACT_CONTEXT_SELECTOR_FINGERPRINT_V2},
        "same_deterministic_selector_context": same_selector_context,
        "one_generation_binding": len(bindings) == 1 and all(bindings),
        "complete_checkpoint_provenance": provenance_complete,
        "no_best_of_selection": True,
    }
    return {
        "schema_version": 1,
        "audit": "priority2_fact_v2_compatibility_reproducibility",
        "official": False,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V7,
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
        "expected_artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "report_paths": [str(path) for path in report_paths],
        "report_sha256": [_file_sha256(path) for path in report_paths],
        "replicate_ids": replicate_ids,
        "generation_bindings": [
            report.get("checkpoint_provenance", {}).get("generation_binding_values")
            for report in reports
        ],
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
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in report_paths]
    report = build_report(reports, list(report_paths))
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
