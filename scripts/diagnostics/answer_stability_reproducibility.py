"""Audit two Answer Stability sentinel reports without provider calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.generation.answer_stability import ANSWER_STABILITY_FINGERPRINT
from src.generation.fact_context import FACT_CONTEXT_SELECTOR_FINGERPRINT


DEFAULT_R1 = Path("data/eval_artifacts/answer_stability_v1_sentinel_summary_r1.json")
DEFAULT_R2 = Path("data/eval_artifacts/answer_stability_v1_sentinel_summary_r2.json")
DEFAULT_OUTPUT = Path(
    "data/diagnostics/answer_stability_reproducibility_v1.json"
)


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _selector_signature(report: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
    return {
        question: (
            row.get("v5_context_sha256"),
            row.get("v6_context_sha256"),
            tuple(row.get("selected_chunk_ids") or ()),
            row.get("selector_tier"),
            row.get("selector_safe"),
            row.get("selector_one_source"),
        )
        for question, row in (report.get("selector_rows") or {}).items()
    }


def build_report(
    first: dict[str, Any],
    second: dict[str, Any],
    first_path: Path | None = None,
    second_path: Path | None = None,
) -> dict[str, Any]:
    first_cases = set(first.get("sentinel_questions") or ())
    second_cases = set(second.get("sentinel_questions") or ())
    first_provenance = first.get("replicate_provenance") or {}
    second_provenance = second.get("replicate_provenance") or {}
    gates = {
        "both_reports_passed": (
            first.get("passed") is True and second.get("passed") is True
        ),
        "same_seven_case_set": (
            len(first_cases) == 7 and first_cases == second_cases
        ),
        "same_stability_fingerprint": (
            first.get("answer_stability_fingerprint")
            == ANSWER_STABILITY_FINGERPRINT
            and second.get("answer_stability_fingerprint")
            == ANSWER_STABILITY_FINGERPRINT
        ),
        "same_selector_fingerprint": (
            first.get("selector_fingerprint") == FACT_CONTEXT_SELECTOR_FINGERPRINT
            and second.get("selector_fingerprint")
            == FACT_CONTEXT_SELECTOR_FINGERPRINT
        ),
        "same_generation_binding": (
            first.get("binding")
            and first.get("binding") == second.get("binding")
            and first_provenance.get("one_generation_binding") is True
            and second_provenance.get("one_generation_binding") is True
        ),
        "same_judge_context_fingerprint": (
            first.get("binding")
            and first.get("binding") == second.get("binding")
            and first_provenance.get("one_judge_context_fingerprint") is True
            and second_provenance.get("one_judge_context_fingerprint") is True
            and first_provenance.get("judge_context_fingerprint_values")
            == second_provenance.get("judge_context_fingerprint_values")
        ),
        "same_selector_outputs": (
            _selector_signature(first) == _selector_signature(second)
        ),
        "both_provider_complete": (
            first.get("provider_complete") is True
            and second.get("provider_complete") is True
        ),
    }
    return {
        "schema_version": 1,
        "audit": "answer_stability_reproducibility_v1",
        "official": False,
        "answer_stability_fingerprint": ANSWER_STABILITY_FINGERPRINT,
        "replicates": [
            {
                "path": str(first_path) if first_path else None,
                "sha256": _file_sha256(first_path) if first_path else None,
                "replicate_id": first.get("replicate_id"),
                "binding": first.get("binding"),
            },
            {
                "path": str(second_path) if second_path else None,
                "sha256": _file_sha256(second_path) if second_path else None,
                "replicate_id": second.get("replicate_id"),
                "binding": second.get("binding"),
            },
        ],
        "gates": gates,
        "passed": all(gates.values()),
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
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
