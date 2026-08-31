"""Run a fresh three-case provider sentinel for Grounded Completion v3.

The sentinel is quota-gated and candidate-only.  It uses the frozen Phase 1
artifact, the production renderer, and isolated generation/judge checkpoints;
it never writes the protected official N=30 result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    assert_phase2_retrieval_hermeticity,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V4,
    render_case_context,
)
from src.evaluation.generation_checkpoint import GenerationCheckpointStore
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.phase2_runtime import (
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_generation_call,
    make_judge_call,
    make_period_value_postprocessor,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import Generator
from src.generation.period_value_completeness import (
    PERIOD_VALUE_CORRECTION_FINGERPRINT,
)


AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
CYBERSECURITY_QUESTION = (
    "Compare the cybersecurity risk disclosures of Apple, Microsoft, and Amazon."
)
AZURE_QUESTION = "How does Microsoft describe its Azure and cloud services growth?"
SENTINEL_QUESTIONS = (
    AWS_QUESTION,
    CYBERSECURITY_QUESTION,
    AZURE_QUESTION,
)
REFERENCE_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")


def sentinel_artifact_paths(replicate_id: str) -> tuple[Path, Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", replicate_id):
        raise ValueError(
            "replicate_id must contain only letters, digits, '-' or '_'"
        )
    prefix = f"data/eval_artifacts/grounded_completion_v3_sentinel_{replicate_id}"
    return (
        Path(prefix + "_gen.jsonl"),
        Path(prefix + "_judge.jsonl"),
        Path(prefix + "_summary.json"),
    )


def sentinel_cases() -> list[TestCase]:
    by_question = {case.question: case for case in TEST_SET}
    missing = [question for question in SENTINEL_QUESTIONS if question not in by_question]
    if missing:
        raise RuntimeError(f"Grounded-completion sentinel contract drift: {missing}")
    return [by_question[question] for question in SENTINEL_QUESTIONS]


def _reference_scores() -> dict[str, dict[str, float]]:
    payload = json.loads(REFERENCE_RESULTS_PATH.read_text(encoding="utf-8"))
    if (
        payload.get("official") is not True
        or payload.get("context_strategy") != "selective_packed_v2"
    ):
        raise RuntimeError("Reference result is not the protected official v2 run")
    result: dict[str, dict[str, float]] = {}
    for case in payload.get("cases", []):
        if case.get("question") not in SENTINEL_QUESTIONS:
            continue
        scores = case.get("scores") or {}
        if all(isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS):
            result[case["question"]] = {
                key: float(scores[key]) for key in SCORE_KEYS
            }
    missing = [question for question in SENTINEL_QUESTIONS if question not in result]
    if missing:
        raise RuntimeError(f"Official reference lacks sentinel scores: {missing}")
    return result


def _aggregate(scores: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        key: round(
            sum(row[key] for row in scores.values()) / max(len(scores), 1), 4
        )
        for key in SCORE_KEYS
    }


def _checkpoint_provenance(
    generation_path: Path,
    judge_path: Path,
    replicate_id: str,
) -> dict[str, Any]:
    generation: dict[str, dict[str, Any]] = {}
    if generation_path.exists():
        for line in generation_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("question") in SENTINEL_QUESTIONS and record.get("status") == "OK":
                generation[record["question"]] = record
    judging: dict[str, dict[str, Any]] = {}
    if judge_path.exists():
        for line in judge_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("question") in SENTINEL_QUESTIONS and record.get("status") == "OK":
                judging[record["question"]] = record
    return {
        "replicate_id": replicate_id,
        "generation_bindings": {
            question: generation[question].get("binding")
            for question in SENTINEL_QUESTIONS
            if question in generation
        },
        "generation_answer_hashes": {
            question: "sha256:" + hashlib.sha256(
                generation[question]["answer"].encode("utf-8")
            ).hexdigest()
            for question in SENTINEL_QUESTIONS
            if question in generation
            and isinstance(generation[question].get("answer"), str)
        },
        "judge_bindings": {
            question: judging[question].get("binding")
            for question in SENTINEL_QUESTIONS
            if question in judging
        },
        "generation_checkpoint": str(generation_path),
        "judge_checkpoint": str(judge_path),
    }


def build_report(
    summary: dict[str, Any],
    correction_rows: dict[str, dict[str, Any]],
    reference: dict[str, dict[str, float]],
) -> dict[str, Any]:
    candidate_scores: dict[str, dict[str, float]] = {}
    case_gates: dict[str, dict[str, Any]] = {}
    for case in summary.get("cases", []):
        question = case.get("question")
        if question not in SENTINEL_QUESTIONS:
            continue
        scores = case.get("scores") or {}
        score_shape = all(isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS)
        if score_shape:
            candidate_scores[question] = {
                key: float(scores[key]) for key in SCORE_KEYS
            }
        deterministic = case.get("deterministic") or {}
        completion = correction_rows.get(question) or {}
        case_gates[question] = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": score_shape,
            "citation_correctness": deterministic.get("citation_correctness"),
            "fallback_correct": deterministic.get("fallback_correct"),
            "recall_proxy": deterministic.get("recall_proxy"),
            "completion_metadata_present": question in correction_rows,
            "completion_final_grounding_passed": completion.get(
                "final_grounding_passed", True
            ) is True,
            "completion_final_unsupported_numeric_claims": completion.get(
                "final_unsupported_numeric_claims", []
            ),
            "completion_correction_at_most_once": completion.get(
                "correction_attempted", False
            ) is not True or completion.get("correction_accepted") is True,
            "reference_scores": reference.get(question),
            "candidate_scores": candidate_scores.get(question),
        }
    candidate_aggregate = (
        _aggregate(candidate_scores)
        if len(candidate_scores) == len(SENTINEL_QUESTIONS)
        else {}
    )
    reference_aggregate = _aggregate(reference)
    provider_complete = bool(
        summary.get("provider_complete")
        and summary.get("num_selected") == len(SENTINEL_QUESTIONS)
        and summary.get("num_generation_ok") == len(SENTINEL_QUESTIONS)
        and summary.get("num_judged_ok") == len(SENTINEL_QUESTIONS)
    )
    deterministic_passed = all(
        row.get("citation_correctness") == 1.0
        and row.get("fallback_correct") is True
        and row.get("recall_proxy") is not False
        and row.get("completion_metadata_present") is True
        and row.get("completion_final_grounding_passed") is True
        and not row.get("completion_final_unsupported_numeric_claims")
        and row.get("completion_correction_at_most_once") is True
        for row in case_gates.values()
    ) and len(case_gates) == len(SENTINEL_QUESTIONS)
    score_regression_passed = all(
        candidate_aggregate.get(key, float("-inf")) >= reference_aggregate[key]
        for key in SCORE_KEYS
    )
    report = {
        **summary,
        "audit": "grounded_completion_v3_sentinel",
        "official": False,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "completion_fingerprint": PERIOD_VALUE_CORRECTION_FINGERPRINT,
        "reference_result": str(REFERENCE_RESULTS_PATH),
        "reference_aggregate": reference_aggregate,
        "candidate_aggregate": candidate_aggregate,
        "case_gates": case_gates,
        "pre_registered_gates": {
            "provider_complete": True,
            "one_shared_binding": True,
            "zero_skipped_or_failed_records": True,
            "deterministic_grounding_and_completion": True,
            "aggregate_scores_not_below_v2_reference": True,
        },
        "gates": {
            "provider_complete": provider_complete,
            "deterministic_passed": deterministic_passed,
            "score_regression_passed": score_regression_passed,
        },
    }
    report["passed"] = all(report["gates"].values())
    return report


def run(
    *,
    replicate_id: str,
    artifact_path: Path = ARTIFACT_PATH,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    output: Path | None = None,
    max_gen_retries: int = 0,
    max_judge_retries: int = 0,
) -> dict[str, Any]:
    assert_phase2_retrieval_hermeticity()
    default_gen, default_judge, default_output = sentinel_artifact_paths(replicate_id)
    gen_checkpoint = gen_checkpoint or default_gen
    judge_checkpoint = judge_checkpoint or default_judge
    output = output or default_output
    artifact, upstream = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V4,
    )
    selected = sentinel_cases()
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    metadata = {case.question: case for case in selected}
    missing = [case.question for case in selected if case.question not in case_by_question]
    if missing:
        raise RuntimeError(f"Artifact lacks sentinel evidence: {missing}")

    def render(case_payload: dict[str, Any]) -> str:
        question = case_payload["question"]
        return render_case_context(
            case_payload,
            required_keywords=metadata[question].required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V4,
        )

    generation_generator = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
    judge_generator = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    tracker = UsageTracker()
    generation_call = make_generation_call(generation_generator, tracker)
    correction_rows: dict[str, dict[str, Any]] = {}
    summary = run_phase2(
        selected=selected,
        case_by_question=case_by_question,
        upstream=upstream,
        bound_fingerprint=EXPECTED_ARTIFACT_FINGERPRINT,
        generate_fn=generation_call,
        judge_fn=make_judge_call(judge_generator, tracker),
        generation_store=GenerationCheckpointStore(gen_checkpoint),
        judge_store=JudgeCheckpointStore(judge_checkpoint),
        max_gen_retries=max_gen_retries,
        max_judge_retries=max_judge_retries,
        evidence_context_fn=render,
        answer_postprocessor=make_period_value_postprocessor(
            generation_call, correction_rows
        ),
        answer_completion_metadata=correction_rows,
        publish_official=False,
    )
    summary["token_usage_totals"] = tracker.totals
    summary["replicate_provenance"] = _checkpoint_provenance(
        gen_checkpoint, judge_checkpoint, replicate_id
    )
    report = build_report(summary, correction_rows, _reference_scores())
    report["replicate_id"] = replicate_id
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replicate-id", required=True)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--gen-checkpoint", type=Path)
    parser.add_argument("--judge-checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    args = parser.parse_args(argv)
    report = run(
        replicate_id=args.replicate_id,
        artifact_path=args.artifact,
        gen_checkpoint=args.gen_checkpoint,
        judge_checkpoint=args.judge_checkpoint,
        output=args.output,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
    )
    _, _, resolved_output = sentinel_artifact_paths(args.replicate_id)
    if args.output is not None:
        resolved_output = args.output
    print(json.dumps({
        "passed": report["passed"],
        "provider_complete": report["gates"]["provider_complete"],
        "deterministic_passed": report["gates"]["deterministic_passed"],
        "score_regression_passed": report["gates"]["score_regression_passed"],
        "candidate_aggregate": report["candidate_aggregate"],
        "reference_aggregate": report["reference_aggregate"],
        "output": str(resolved_output),
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
