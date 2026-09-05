"""Audit two Comparative Answerability Guard v1 sentinel replicates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from src.evaluation.evidence_provenance import (
    exact_records,
    file_same,
    file_sha256,
    read_jsonl,
    valid_score,
)
from scripts.run_answerability_stability_sentinel import SENTINEL_QUESTIONS
from scripts.run_answerability_stability_sentinel import (
    EXPECTED_REFERENCE_SHA256,
    REFERENCE_PATH,
    TARGET_QUESTION,
    RISK_CONTROL_QUESTION,
    OUT_OF_CORPUS_QUESTION,
)
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
    COMPARATIVE_ANSWERABILITY_V3_FINGERPRINT,
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
    return read_jsonl(path)


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


def _text_sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mean_scores(cases: dict[str, dict[str, Any]]) -> dict[str, float] | None:
    keys = ("faithfulness", "answer_relevancy", "context_precision")
    values: dict[str, list[float]] = {key: [] for key in keys}
    for question in SENTINEL_QUESTIONS:
        scores = cases[question].get("scores")
        if not isinstance(scores, dict) or any(not valid_score(scores.get(key)) for key in keys):
            return None
        for key in keys:
            values[key].append(float(scores[key]))
    return {key: round(sum(items) / len(items), 4) for key, items in values.items()}


def _v3_reference_scores() -> dict[str, dict[str, float]]:
    if not REFERENCE_PATH.exists() or file_sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        return {}
    try:
        payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    result: dict[str, dict[str, float]] = {}
    for case in payload.get("cases", []):
        scores = case.get("scores") if isinstance(case, dict) else None
        if isinstance(case, dict) and isinstance(case.get("question"), str) and isinstance(scores, dict):
            if all(valid_score(scores.get(key)) for key in ("faithfulness", "answer_relevancy", "context_precision")):
                result[case["question"]] = {key: float(scores[key]) for key in ("faithfulness", "answer_relevancy", "context_precision")}
    return result


def _validate_v3_contract(
    report: dict[str, Any],
    report_path: Path,
    generation_path: Path,
    judge_path: Path,
    generation_records: list[dict[str, Any]],
    judge_records: list[dict[str, Any]],
) -> tuple[str, ...]:
    """Validate a v3 receipt from source records, never from ``passed``."""
    errors: list[str] = []
    if report.get("schema_version") != 3:
        errors.append("Evidence Contract v3 report schema_version must be 3")
    if report.get("evaluation_profile") != "evidence-contract-v3":
        errors.append("Evidence Contract v3 evaluation profile is missing")
    run_id = report.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        errors.append("v3 report run_id is missing")

    cases, case_errors = exact_records(report.get("cases"), SENTINEL_QUESTIONS, "report cases")
    errors.extend(case_errors)
    for question, case in cases.items():
        if not isinstance(case.get("answer"), str):
            errors.append(f"report answer is missing or not a string: {question}")
        scores = case.get("scores")
        if not isinstance(scores, dict):
            errors.append(f"report scores are missing: {question}")
        else:
            for key in ("faithfulness", "answer_relevancy", "context_precision"):
                if not valid_score(scores.get(key)):
                    errors.append(f"report score is invalid for {question}: {key}")

    generations, generation_case_errors = exact_records(
        generation_records, SENTINEL_QUESTIONS, "generation checkpoint"
    )
    judges, judge_case_errors = exact_records(
        judge_records, SENTINEL_QUESTIONS, "judge checkpoint"
    )
    errors.extend(generation_case_errors)
    errors.extend(judge_case_errors)
    if file_same(generation_path, judge_path):
        errors.append("generation and judge checkpoints resolve to the same file identity")

    for label, records in (("generation", generations), ("judge", judges)):
        for question, record in records.items():
            if record.get("run_id") != run_id:
                errors.append(f"{label} run_id mismatch: {question}")
            if record.get("status") != "OK":
                errors.append(f"{label} record is not OK: {question}")

    for question in SENTINEL_QUESTIONS:
        generation = generations.get(question)
        judge = judges.get(question)
        case = cases.get(question)
        if not isinstance(generation, dict) or not isinstance(judge, dict) or not isinstance(case, dict):
            continue
        if generation.get("answer") != case.get("answer"):
            errors.append(f"report answer differs from generation checkpoint: {question}")
        if judge.get("scores") != case.get("scores"):
            errors.append(f"report score differs from judge checkpoint: {question}")

        # Recompute generation binding from the recorded inputs. A copied or
        # edited binding cannot be accepted merely because all rows agree.
        inputs = generation.get("binding_inputs")
        if not isinstance(inputs, dict):
            errors.append(f"generation binding inputs are missing: {question}")
        else:
            try:
                from src.evaluation.evidence_contract_v3 import compute_generation_binding_v3
                expected = compute_generation_binding_v3(**inputs)
            except (TypeError, ValueError, KeyError) as error:
                errors.append(f"generation binding inputs invalid: {question} ({error})")
            else:
                if generation.get("binding") != expected:
                    errors.append(f"generation binding recomputation mismatch: {question}")

        # Judge identity binds the actual rendered context, reference, rubric,
        # answer, and prompt. It is deliberately per-case rather than a
        # batch-wide binding so one changed answer cannot hide in an aggregate.
        try:
            from src.evaluation.evidence_contract_v3 import (
                compute_judge_binding_v3,
                reference_for,
            )
            context_rows = report.get("context_rows")
            row = context_rows.get(question) if isinstance(context_rows, dict) else None
            context = row.get("context") if isinstance(row, dict) else None
            prompt_sha = judge.get("prompt_sha256")
            if not isinstance(context, str) or not isinstance(prompt_sha, str):
                raise ValueError("context or prompt hash is missing")
            expected_judge = compute_judge_binding_v3(
                generation_binding=generation.get("binding"),
                question=question,
                answer=case.get("answer"),
                context=context,
                reference=reference_for(question),
                judge_model=judge.get("model"),
                prompt_sha256=prompt_sha,
                judge_max_tokens=judge.get("judge_max_tokens"),
            )
            if judge.get("binding") != expected_judge:
                errors.append(f"judge binding recomputation mismatch: {question}")
        except (AttributeError, TypeError, ValueError, KeyError) as error:
            errors.append(f"judge binding inputs invalid: {question} ({error})")

    # Re-render the context from the locked artifact and compare both bytes
    # and identity metadata. The stored context is an audit receipt, not the
    # authority that defines what was retrieved.
    provenance = report.get("checkpoint_provenance") or {}
    artifact_value = report.get("artifact_path")
    if not isinstance(artifact_value, str):
        errors.append("v3 artifact_path is missing")
    else:
        artifact_path = Path(artifact_value)
        try:
            artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            actual_artifact_hash = file_sha256(artifact_path)
            if report.get("artifact_sha256") != actual_artifact_hash:
                errors.append("v3 artifact hash does not match the locked artifact")
            actual_embedded = (artifact_payload.get("fingerprints") or {}).get("artifact")
            if report.get("artifact_fingerprint") != actual_embedded:
                errors.append("v3 artifact fingerprint does not match the locked artifact")
            from src.evaluation.context_packing import render_case_context
            from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V7
            artifact_cases = {item.get("question"): item for item in artifact_payload.get("cases", [])}
            rows = report.get("context_rows")
            if not isinstance(rows, dict) or set(rows) != set(SENTINEL_QUESTIONS):
                errors.append("v3 context_rows do not exactly cover the registered questions")
            else:
                for question in SENTINEL_QUESTIONS:
                    row = rows.get(question)
                    payload = artifact_cases.get(question)
                    if not isinstance(row, dict) or not isinstance(payload, dict):
                        errors.append(f"v3 context row or artifact case is missing: {question}")
                        continue
                    expected_context = render_case_context(
                        payload,
                        required_keywords=payload.get("required_keywords") or (),
                        strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
                    )
                    if row.get("context") != expected_context:
                        errors.append(f"rendered context mismatch: {question}")
                    if row.get("context_sha256") != _text_sha256(expected_context):
                        errors.append(f"rendered context hash mismatch: {question}")
                    if row.get("source_count") != len(re.findall(r"(?m)^\[Source \d+\] ", expected_context)):
                        errors.append(f"rendered context source count mismatch: {question}")
                    if row.get("context_fingerprint") != report.get("context_builder_fingerprint"):
                        errors.append(f"context fingerprint mismatch: {question}")
        except (AttributeError, OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f"cannot re-render v3 context: {error}")

    metrics = report.get("metrics")
    recomputed_metrics = _mean_scores(cases) if len(cases) == len(SENTINEL_QUESTIONS) else None
    if metrics != recomputed_metrics:
        errors.append("aggregate metrics do not match the case scores")
    reference_scores = _v3_reference_scores()
    controls = [
        question for question in SENTINEL_QUESTIONS
        if question not in {TARGET_QUESTION, RISK_CONTROL_QUESTION, OUT_OF_CORPUS_QUESTION}
    ]
    def case_score(question: str, key: str) -> Any:
        case = cases.get(question)
        scores = case.get("scores") if isinstance(case, dict) else None
        return scores.get(key) if isinstance(scores, dict) else None

    expected_gates = {
        "all_generation_ok": len(generations) == len(SENTINEL_QUESTIONS)
        and all(record.get("status") == "OK" for record in generations.values()),
        "all_judge_ok": len(judges) == len(SENTINEL_QUESTIONS)
        and all(record.get("status") == "OK" for record in judges.values()),
        "all_faithfulness_exact_one": recomputed_metrics is not None
        and all(case_score(question, "faithfulness") == 1.0 for question in SENTINEL_QUESTIONS),
        "dependency_answer_relevancy_exact_one": (
            case_score(TARGET_QUESTION, "answer_relevancy") == 1.0
        ),
        "risk_answer_relevancy_floor": (
            isinstance(case_score(RISK_CONTROL_QUESTION, "answer_relevancy"), (int, float))
            and case_score(RISK_CONTROL_QUESTION, "answer_relevancy") >= 0.95
        ),
        "controls_answer_relevancy_drift_bounded": (
            bool(reference_scores)
            and all(
                question in cases
                and question in reference_scores
                and case_score(question, "answer_relevancy")
                >= reference_scores[question]["answer_relevancy"] - 0.05
                for question in controls
            )
        ),
        "out_of_corpus_fallback_preserved": (
            isinstance(cases.get(OUT_OF_CORPUS_QUESTION, {}).get("answer") if isinstance(cases.get(OUT_OF_CORPUS_QUESTION), dict) else None, str)
            and "could not find sufficient information" in cases[OUT_OF_CORPUS_QUESTION]["answer"].casefold()
        ),
        "aggregate_faithfulness_exact_one": recomputed_metrics is not None
        and recomputed_metrics["faithfulness"] == 1.0,
        "aggregate_answer_relevancy_floor": recomputed_metrics is not None
        and recomputed_metrics["answer_relevancy"] >= 0.975,
        "aggregate_context_precision_floor": recomputed_metrics is not None
        and recomputed_metrics["context_precision"] >= 0.67,
    }
    if report.get("recomputed_gates") != expected_gates:
        errors.append("recomputed gates do not match source records")
    if report.get("passed") is not (all(expected_gates.values()) and not errors):
        errors.append("reported passed flag disagrees with recomputed integrity gates")
    return tuple(dict.fromkeys(errors))


def validate_report(report: dict[str, Any], report_path: Path) -> tuple[str, ...]:
    """Validate one replicate from its report and both append-only stores."""
    errors: list[str] = []
    if not isinstance(report, dict):
        return ("report must be a JSON object",)
    report_cases, report_case_errors = exact_records(
        report.get("cases"), SENTINEL_QUESTIONS, "report cases"
    )
    errors.extend(report_case_errors)
    if list(report.get("sentinel_questions") or ()) != list(SENTINEL_QUESTIONS):
        errors.append("sentinel_questions do not exactly match the registered set")
    registered_strategy = report.get("candidate_strategy") or report.get("context_strategy")
    if registered_strategy != CANDIDATE_STRATEGY:
        errors.append("candidate strategy is not the registered strategy")
    is_v3 = report.get("schema_version") == 3 or isinstance(report.get("run_id"), str)
    for field, expected in (
        ("answer_completion_fingerprint", ANSWER_COMPLETION_FINGERPRINT),
        (
            "answerability_fingerprint",
            COMPARATIVE_ANSWERABILITY_V3_FINGERPRINT
            if is_v3
            else COMPARATIVE_ANSWERABILITY_FINGERPRINT,
        ),
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
    if file_same(generation_path, judge_path):
        errors.append("generation and judge checkpoints are the same file identity")

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
    summary_cases = report_cases
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
        elif not is_v3:
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
    if is_v3:
        errors.extend(
            _validate_v3_contract(
                report,
                report_path,
                generation_path,
                judge_path,
                generation_records,
                judge_records,
            )
        )
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
    is_v3 = any(
        report.get("schema_version") == 3 or isinstance(report.get("run_id"), str)
        for report in (first, second)
    )
    v3_integrity_pass = (
        not first_integrity_errors
        and not second_integrity_errors
        and all((first.get("recomputed_gates") or {}).values())
        and all((second.get("recomputed_gates") or {}).values())
    )
    gates = {
        "both_reports_passed": (
            v3_integrity_pass
            if is_v3
            else first.get("passed") is True and second.get("passed") is True
        ),
        "same_sentinel_set": (
            set(first.get("sentinel_questions") or ())
            == set(second.get("sentinel_questions") or ())
            == set(SENTINEL_QUESTIONS)
        ),
        "distinct_replicates": (
            first.get("run_id") != second.get("run_id")
            if is_v3
            else first.get("replicate_id") != second.get("replicate_id")
        ),
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
            not file_same(
                _path_from_report(first_provenance.get("generation_checkpoint")),
                _path_from_report(second_provenance.get("generation_checkpoint")),
            )
            and not file_same(
                _path_from_report(first_provenance.get("judge_checkpoint")),
                _path_from_report(second_provenance.get("judge_checkpoint")),
            )
            if _path_from_report(first_provenance.get("generation_checkpoint"))
            and _path_from_report(second_provenance.get("generation_checkpoint"))
            and _path_from_report(first_provenance.get("judge_checkpoint"))
            and _path_from_report(second_provenance.get("judge_checkpoint"))
            else False
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
    try:
        report = run(args.r1, args.r2, args.output)
    except Exception as error:  # noqa: BLE001 - verifier must fail closed
        report = {
            "schema_version": 3,
            "audit": "comparative_answerability_stability_v1_reproducibility",
            "official": False,
            "passed": False,
            "provenance_errors": {"fatal": [f"verifier failed closed: {error}"]},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
