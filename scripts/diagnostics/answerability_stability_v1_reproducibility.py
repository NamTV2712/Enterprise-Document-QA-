"""Audit two Comparative Answerability Guard v1 sentinel replicates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_answerability_stability_sentinel import SENTINEL_QUESTIONS
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
)


DEFAULT_R1 = Path(
    "data/eval_artifacts/answerability_stability_v1_sentinel_summary_r1.json"
)
DEFAULT_R2 = Path(
    "data/eval_artifacts/answerability_stability_v1_sentinel_summary_r2.json"
)
DEFAULT_OUTPUT = Path(
    "data/diagnostics/answerability_stability_v1_reproducibility.json"
)
CANDIDATE_STRATEGY = "selective_packed_v7_fact_generalization_candidate"


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _signature(report: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
    context_rows = report.get("context_rows") or {}
    return {
        question: (
            row.get("context_sha256"),
            row.get("source_count"),
            row.get("context_deterministic"),
        )
        for question, row in context_rows.items()
        if isinstance(row, dict)
    }


def build_report(
    first: dict[str, Any],
    second: dict[str, Any],
    first_path: Path,
    second_path: Path,
) -> dict[str, Any]:
    first_provenance = first.get("checkpoint_provenance") or {}
    second_provenance = second.get("checkpoint_provenance") or {}
    gates = {
        "both_reports_passed": (
            first.get("passed") is True and second.get("passed") is True
        ),
        "same_sentinel_set": (
            set(first.get("sentinel_questions") or ())
            == set(second.get("sentinel_questions") or ())
            == set(SENTINEL_QUESTIONS)
        ),
        "distinct_replicates": first.get("replicate_id") != second.get("replicate_id"),
        "same_strategy": (
            first.get("context_strategy") == CANDIDATE_STRATEGY
            and second.get("context_strategy") == CANDIDATE_STRATEGY
        ),
        "same_completion_fingerprint": (
            first.get("answer_completion_fingerprint") == ANSWER_COMPLETION_FINGERPRINT
            and second.get("answer_completion_fingerprint") == ANSWER_COMPLETION_FINGERPRINT
        ),
        "same_answerability_fingerprint": (
            first.get("answerability_fingerprint")
            == COMPARATIVE_ANSWERABILITY_FINGERPRINT
            and second.get("answerability_fingerprint")
            == COMPARATIVE_ANSWERABILITY_FINGERPRINT
        ),
        "same_generation_binding": (
            first.get("binding")
            and first.get("binding") == second.get("binding")
            and first_provenance.get("one_generation_binding") is True
            and second_provenance.get("one_generation_binding") is True
        ),
        "same_judge_context_fingerprint": (
            first_provenance.get("one_judge_context_fingerprint") is True
            and second_provenance.get("one_judge_context_fingerprint") is True
        ),
        "same_context_outputs": _signature(first) == _signature(second),
        "both_provider_complete": (
            first.get("provider_complete") is True
            and second.get("provider_complete") is True
        ),
    }
    gates["all_replicates_pass"] = all(gates.values())
    return {
        "schema_version": 1,
        "audit": "comparative_answerability_stability_v1_reproducibility",
        "official": False,
        "candidate_strategy": CANDIDATE_STRATEGY,
        "pre_registered_rule": {
            "minimum_replicates": 2,
            "required_pass_rate": 1.0,
            "best_of_selection_forbidden": True,
        },
        "completion_fingerprints": [ANSWER_COMPLETION_FINGERPRINT],
        "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_FINGERPRINT,
        "replicates": [
            {
                "path": str(first_path),
                "sha256": _file_sha256(first_path),
                "replicate_id": first.get("replicate_id"),
                "binding": first.get("binding"),
            },
            {
                "path": str(second_path),
                "sha256": _file_sha256(second_path),
                "replicate_id": second.get("replicate_id"),
                "binding": second.get("binding"),
            },
        ],
        "gates": gates,
        "passed": gates["all_replicates_pass"],
    }


def run(
    first_path: Path = DEFAULT_R1,
    second_path: Path = DEFAULT_R2,
    output: Path | None = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    first = json.loads(first_path.read_text(encoding="utf-8"))
    second = json.loads(second_path.read_text(encoding="utf-8"))
    report = build_report(first, second, first_path, second_path)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--r2", type=Path, default=DEFAULT_R2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(args.r1, args.r2, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
