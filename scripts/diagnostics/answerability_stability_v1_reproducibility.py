"""Audit two Comparative Answerability Guard v1 sentinel replicates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.run_answerability_stability_sentinel import SENTINEL_QUESTIONS
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
)
from src.evaluation.generation_checkpoint import sha256_text
from src.evaluation.judge_checkpoint import compute_judge_binding
from src.evaluation.phase2_runtime import JUDGE_CONTEXT_BUILDER_FINGERPRINT


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
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


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


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    if not path.exists():
        return [], (f"checkpoint does not exist: {path}",)
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"{path}:{line_number}: invalid JSON ({error})")
            continue
        if not isinstance(record, dict):
            errors.append(f"{path}:{line_number}: record is not an object")
            continue
        records.append(record)
    return records, tuple(errors)


def _path_from_report(value: Any) -> Path | None:
    return Path(value) if isinstance(value, str) and value else None


def _checkpoint_field_by_question(
    path: Path | None,
    field: str,
) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    records, _ = _read_jsonl(path)
    return {
        record["question"]: record.get(field)
        for record in records
        if record.get("question") in SENTINEL_QUESTIONS
    }


def validate_report(report: dict[str, Any], report_path: Path) -> tuple[str, ...]:
    """Validate one replicate from its report and both append-only stores."""
    errors: list[str] = []
    if list(report.get("sentinel_questions") or ()) != list(SENTINEL_QUESTIONS):
        errors.append("sentinel_questions do not exactly match the registered set")
    registered_strategy = report.get("candidate_strategy") or report.get("context_strategy")
    if registered_strategy != CANDIDATE_STRATEGY:
        errors.append("candidate strategy is not the registered strategy")
    for field, expected in (
        ("answer_completion_fingerprint", ANSWER_COMPLETION_FINGERPRINT),
        ("answerability_fingerprint", COMPARATIVE_ANSWERABILITY_FINGERPRINT),
    ):
        if report.get(field) != expected:
            errors.append(f"{field} does not match the current contract")

    context_rows = report.get("context_rows")
    if not isinstance(context_rows, dict) or set(context_rows) != set(SENTINEL_QUESTIONS):
        errors.append("context_rows are missing or do not cover every sentinel question")
    else:
        for question in SENTINEL_QUESTIONS:
            row = context_rows[question]
            if not isinstance(row, dict):
                errors.append(f"context row is not an object: {question}")
                continue
            if not _SHA256_RE.fullmatch(str(row.get("context_sha256", ""))):
                errors.append(f"context hash is invalid: {question}")
            if not isinstance(row.get("source_count"), int) or row["source_count"] <= 0:
                errors.append(f"context source count is invalid: {question}")
            if row.get("context_deterministic") is not True:
                errors.append(f"context is not proven deterministic: {question}")

    provenance = report.get("checkpoint_provenance")
    if not isinstance(provenance, dict):
        errors.append("checkpoint_provenance is missing")
        return tuple(errors)
    generation_path = _path_from_report(provenance.get("generation_checkpoint"))
    judge_path = _path_from_report(provenance.get("judge_checkpoint"))
    if generation_path is None or judge_path is None:
        errors.append("checkpoint paths are missing")
        return tuple(errors)
    if generation_path.resolve() == judge_path.resolve():
        errors.append("generation and judge checkpoints are the same file")

    generation_records, generation_errors = _read_jsonl(generation_path)
    judge_records, judge_errors = _read_jsonl(judge_path)
    errors.extend(generation_errors)
    errors.extend(judge_errors)
    expected_binding = report.get("binding")
    generations = [
        record for record in generation_records
        if record.get("question") in SENTINEL_QUESTIONS
    ]
    judges = [
        record for record in judge_records
        if record.get("question") in SENTINEL_QUESTIONS
    ]
    if len(generation_records) != len(SENTINEL_QUESTIONS) or {
        record.get("question") for record in generation_records
    } != set(SENTINEL_QUESTIONS):
        errors.append("generation checkpoint does not contain exactly one record per question")
    if len(judge_records) != len(SENTINEL_QUESTIONS) or {
        record.get("question") for record in judge_records
    } != set(SENTINEL_QUESTIONS):
        errors.append("judge checkpoint does not contain exactly one record per question")
    generation_by_question = {record.get("question"): record for record in generations}
    judge_by_question = {record.get("question"): record for record in judges}
    summary_cases = {
        case.get("question"): case
        for case in report.get("cases", [])
        if isinstance(case, dict)
    }
    for question in SENTINEL_QUESTIONS:
        generation = generation_by_question.get(question)
        judge = judge_by_question.get(question)
        if not isinstance(generation, dict) or generation.get("status") != "OK":
            errors.append(f"generation record is not OK: {question}")
        else:
            if generation.get("binding") != expected_binding:
                errors.append(f"generation binding mismatch: {question}")
            if generation.get("answer_completion_fingerprint") != report.get(
                "answer_completion_fingerprint"
            ):
                errors.append(f"generation completion fingerprint mismatch: {question}")
            summary_case = summary_cases.get(question)
            if isinstance(summary_case, dict) and summary_case.get("answer") != generation.get("answer"):
                errors.append(f"summary answer differs from generation checkpoint: {question}")
        if not isinstance(judge, dict) or judge.get("status") != "OK":
            errors.append(f"judge record is not OK: {question}")
        elif judge.get("judge_context_fingerprint") != JUDGE_CONTEXT_BUILDER_FINGERPRINT:
            errors.append(f"judge context fingerprint mismatch: {question}")
        else:
            generation_binding = generation.get("binding") if isinstance(generation, dict) else None
            answer = generation.get("answer") if isinstance(generation, dict) else None
            judge_model = judge.get("model")
            judge_template = judge.get("judge_prompt_template_sha256")
            judge_max_tokens = judge.get("judge_max_tokens")
            if not (
                isinstance(generation_binding, str)
                and isinstance(answer, str)
                and isinstance(judge_model, str)
                and isinstance(judge_template, str)
                and isinstance(judge_max_tokens, int)
            ):
                errors.append(f"judge binding inputs are incomplete: {question}")
            else:
                expected_judge_binding = compute_judge_binding(
                    generation_binding=generation_binding,
                    generation_answer_sha256s=sha256_text(json.dumps(
                        [sha256_text(answer)],
                        separators=(",", ":"),
                    )),
                    judge_model=judge_model,
                    judge_prompt_template_sha256=judge_template,
                    judge_max_tokens=judge_max_tokens,
                    judge_context_fingerprint=JUDGE_CONTEXT_BUILDER_FINGERPRINT,
                )
                if judge.get("binding") != expected_judge_binding:
                    errors.append(f"judge binding mismatch: {question}")

    actual_generation_bindings = sorted({
        record.get("binding")
        for record in generation_records
        if isinstance(record.get("binding"), str)
    })
    actual_judge_contexts = sorted({
        record.get("judge_context_fingerprint")
        for record in judge_records
        if isinstance(record.get("judge_context_fingerprint"), str)
    })
    actual_judge_bindings = sorted({
        record.get("binding")
        for record in judges
        if isinstance(record.get("binding"), str)
    })
    if actual_generation_bindings != [expected_binding]:
        errors.append("generation checkpoint contains unexpected bindings")
    if actual_judge_contexts != [JUDGE_CONTEXT_BUILDER_FINGERPRINT]:
        errors.append("judge checkpoint does not have one registered context fingerprint")
    if not actual_judge_bindings:
        errors.append("judge checkpoint contains no binding")
    if provenance.get("generation_bindings") != actual_generation_bindings:
        errors.append("report generation bindings do not match checkpoint bindings")
    if provenance.get("judge_context_fingerprints") != actual_judge_contexts:
        errors.append("report judge context fingerprints do not match checkpoint")
    if provenance.get("judge_bindings") != actual_judge_bindings:
        errors.append("report judge bindings do not match checkpoint")
    return tuple(errors)


def build_report(
    first: dict[str, Any],
    second: dict[str, Any],
    first_path: Path,
    second_path: Path,
) -> dict[str, Any]:
    first_provenance = first.get("checkpoint_provenance") or {}
    second_provenance = second.get("checkpoint_provenance") or {}
    first_integrity_errors = validate_report(first, first_path)
    second_integrity_errors = validate_report(second, second_path)
    first_judge_bindings = _checkpoint_field_by_question(
        _path_from_report(first_provenance.get("judge_checkpoint")),
        "binding",
    )
    second_judge_bindings = _checkpoint_field_by_question(
        _path_from_report(second_provenance.get("judge_checkpoint")),
        "binding",
    )
    first_answers = {
        case.get("question"): case.get("answer")
        for case in first.get("cases", [])
        if isinstance(case, dict)
    }
    second_answers = {
        case.get("question"): case.get("answer")
        for case in second.get("cases", [])
        if isinstance(case, dict)
    }
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
            first_provenance.get("judge_context_fingerprints")
            == second_provenance.get("judge_context_fingerprints")
            == [JUDGE_CONTEXT_BUILDER_FINGERPRINT]
        ),
        "same_context_outputs": _signature(first) == _signature(second),
        "first_report_integrity": not first_integrity_errors,
        "second_report_integrity": not second_integrity_errors,
        "distinct_checkpoint_paths": (
            first_provenance.get("generation_checkpoint")
            != second_provenance.get("generation_checkpoint")
            and first_provenance.get("judge_checkpoint")
            != second_provenance.get("judge_checkpoint")
        ),
        "same_judge_bindings_for_identical_answers": (
            bool(first_provenance.get("judge_bindings"))
            and bool(second_provenance.get("judge_bindings"))
            and all(
                first_answers.get(question) != second_answers.get(question)
                or first_judge_bindings.get(question) == second_judge_bindings.get(question)
                for question in SENTINEL_QUESTIONS
            )
        ),
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
        "provenance_errors": {
            "first": list(first_integrity_errors),
            "second": list(second_integrity_errors),
        },
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
