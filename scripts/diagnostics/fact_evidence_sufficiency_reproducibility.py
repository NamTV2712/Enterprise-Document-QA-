"""Verify the two pre-registered fact-evidence sentinel replicates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import EXPECTED_ARTIFACT_FINGERPRINT
from scripts.run_fact_evidence_sufficiency_sentinel import SENTINEL_QUESTIONS
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V6
from src.generation.fact_context import FACT_CONTEXT_SELECTOR_FINGERPRINT


DEFAULT_OUTPUT = Path(
    "data/diagnostics/fact_evidence_sufficiency_reproducibility_v1.json"
)
DEFAULT_REPORTS = (
    Path("data/eval_artifacts/fact_evidence_sufficiency_v1_sentinel_summary_r1.json"),
    Path("data/eval_artifacts/fact_evidence_sufficiency_v1_sentinel_summary_r2.json"),
)
EXPECTED_REPLICATES = 2


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _all_true(mapping: Any) -> bool:
    return isinstance(mapping, dict) and bool(mapping) and all(
        value is True for value in mapping.values()
    )


def _checkpoint_hashes_match(report: dict[str, Any]) -> bool:
    provenance = report.get("replicate_provenance")
    if not isinstance(provenance, dict):
        return False
    checks = (
        ("generation_checkpoint", "generation_checkpoint_sha256"),
        ("judge_checkpoint", "judge_checkpoint_sha256"),
    )
    for path_key, hash_key in checks:
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
    bindings = {report.get("binding") for report in reports}
    upstream_artifacts = {
        report.get("upstream_artifact_sha256") for report in reports
    }
    selector_fingerprints = {
        report.get("selector_fingerprint") for report in reports
    }
    selector_rows = [report.get("selector_rows") or {} for report in reports]
    selector_context_keys = (
        "selector_tier",
        "selected_chunk_ids",
        "source_count",
        "context_sha256",
        "safe",
    )
    same_selector_context = (
        len(selector_rows) == EXPECTED_REPLICATES
        and {
            question: {
                key: selector_rows[0].get(question, {}).get(key)
                for key in selector_context_keys
            }
            for question in SENTINEL_QUESTIONS
        }
        == {
            question: {
                key: selector_rows[1].get(question, {}).get(key)
                for key in selector_context_keys
            }
            for question in SENTINEL_QUESTIONS
        }
    ) if len(selector_rows) == EXPECTED_REPLICATES else False
    provenance_complete = all(
        isinstance(report.get("replicate_provenance"), dict)
        and _checkpoint_hashes_match(report)
        and report["replicate_provenance"].get("generation_checkpoint_sha256")
        and report["replicate_provenance"].get("judge_checkpoint_sha256")
        and len(report["replicate_provenance"].get("generation_binding_values", [])) == 1
        and len(report["replicate_provenance"].get("judge_binding_values", [])) == 4
        and len(report["replicate_provenance"].get("judge_context_fingerprint_values", [])) == 1
        and report["replicate_provenance"].get("one_generation_binding") is True
        and report["replicate_provenance"].get("judge_records_complete") is True
        and report["replicate_provenance"].get("one_judge_context_fingerprint") is True
        for report in reports
    )
    all_replicates_pass = len(reports) == EXPECTED_REPLICATES and all(
        report.get("passed") is True
        and report.get("official") is False
        and report.get("provider_complete") is True
        and report.get("context_strategy") == CONTEXT_STRATEGY_SELECTIVE_V6
        and tuple(report.get("sentinel_questions") or ()) == SENTINEL_QUESTIONS
        and _all_true(report.get("gates"))
        for report in reports
    )
    gates = {
        "exactly_two_replicates": len(reports) == EXPECTED_REPLICATES,
        "unique_replicate_ids": len(replicate_ids) == len(set(replicate_ids))
        and all(isinstance(value, str) and value for value in replicate_ids),
        "all_replicates_pass": all_replicates_pass,
        "one_strategy": len(bindings) == 1 and None not in bindings,
        "one_upstream_artifact": len(upstream_artifacts) == 1
        and None not in upstream_artifacts,
        "one_selector_fingerprint": selector_fingerprints
        == {FACT_CONTEXT_SELECTOR_FINGERPRINT},
        "same_deterministic_selector_context": same_selector_context,
        "complete_checkpoint_provenance": provenance_complete,
        "no_best_of_selection": True,
    }
    return {
        "schema_version": 1,
        "audit": "fact_evidence_sufficiency_reproducibility_v1",
        "official": False,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT,
        "expected_artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "report_paths": [str(path) for path in report_paths],
        "report_sha256": [_file_sha256(path) for path in report_paths],
        "replicate_ids": replicate_ids,
        "generation_bindings": [report.get("binding") for report in reports],
        "pre_registered_rule": {
            "minimum_replicates": EXPECTED_REPLICATES,
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
