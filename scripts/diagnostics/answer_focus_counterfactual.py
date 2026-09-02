"""Run the provider-free answer-focus counterfactual for the V7 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import ARTIFACT_PATH, load_bound_artifact
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET
from src.generation.answer_completion import (
    completion_metadata,
    correct_answer_once,
)
from src.generation.enumeration_completeness import assess_enumeration_completeness


CANDIDATE_PATH = Path(
    "data/eval_artifacts/phase2_results_answer_stability_v7_candidate.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/answer_focus_counterfactual_v1.json")
TARGET_QUESTION = "What are all the major risk factors Microsoft discloses?"


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _case_map(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        case["question"]: case
        for case in document.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("question"), str)
    }


def build_report(
    candidate: dict[str, Any],
    artifact: dict[str, Any],
    *,
    candidate_path: Path = CANDIDATE_PATH,
    artifact_path: Path = ARTIFACT_PATH,
) -> dict[str, Any]:
    test_cases = {
        test_case.question: test_case
        for test_case in TEST_SET
        if test_case.priority <= 2
    }
    artifact_cases = _case_map(artifact)
    candidate_cases = _case_map(candidate)
    rows: list[dict[str, Any]] = []
    provider_calls = 0
    for question in test_cases:
        test_case = test_cases[question]
        case = candidate_cases[question]
        context = render_case_context(
            artifact_cases[question],
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )

        def unexpected_provider_call(_: str) -> str:
            nonlocal provider_calls
            provider_calls += 1
            raise AssertionError("counterfactual must not call a provider")

        outcome = correct_answer_once(
            question,
            context,
            case.get("answer") or "",
            unexpected_provider_call,
        )
        risk = assess_enumeration_completeness(
            question, context, outcome.answer
        )
        rows.append(
            {
                "question": question,
                "category": test_case.category,
                "context_sha256": _sha256_text(context),
                "source_boundary_parse_passed": bool(
                    parse_evidence_context(context)
                ),
                "original_answer_sha256": _sha256_text(case.get("answer") or ""),
                "counterfactual_answer_sha256": _sha256_text(outcome.answer),
                "changed": outcome.answer != (case.get("answer") or ""),
                "provider_call_attempted": outcome.correction_attempted,
                "answer_compacted": outcome.answer_compacted,
                "completion": completion_metadata(outcome),
                "risk_overdetailed": risk.overdetailed,
                "risk_missing_items": [
                    item.label for item in risk.missing_items
                ],
            }
        )

    changed = [row["question"] for row in rows if row["changed"]]
    target = next(row for row in rows if row["question"] == TARGET_QUESTION)
    gates = {
        "candidate_complete": len(rows) == 30,
        "provider_free": provider_calls == 0
        and all(not row["provider_call_attempted"] for row in rows),
        "source_boundaries_valid": all(
            row["source_boundary_parse_passed"] for row in rows
        ),
        "only_risk_target_changes": changed == [TARGET_QUESTION],
        "risk_target_compacted": (
            target["answer_compacted"]
            and target["risk_overdetailed"] is False
            and target["risk_missing_items"] == []
        ),
        "non_target_completion_passed": all(
            row["completion"]["final_passed"] is True
            for row in rows
            if row["question"] != TARGET_QUESTION
        ),
    }
    return {
        "schema_version": 1,
        "audit": "answer_focus_counterfactual_v1",
        "official": False,
        "candidate_path": str(candidate_path),
        "candidate_sha256": _sha256_bytes(candidate_path.read_bytes()),
        "artifact_path": str(artifact_path),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "target_question": TARGET_QUESTION,
        "num_cases": len(rows),
        "changed_questions": changed,
        "cases": rows,
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    *,
    candidate_path: Path = CANDIDATE_PATH,
    artifact_path: Path = ARTIFACT_PATH,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    artifact, _ = load_bound_artifact(
        artifact_path,
        candidate.get("bound_artifact_fingerprint"),
        CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    report = build_report(
        candidate,
        artifact,
        candidate_path=candidate_path,
        artifact_path=artifact_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_PATH)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(
        candidate_path=args.candidate,
        artifact_path=args.artifact,
        output=args.output,
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
