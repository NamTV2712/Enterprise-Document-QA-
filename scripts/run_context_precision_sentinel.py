"""Run the four-case provider sentinel for a context-packing candidate.

This is the quota-gated follow-up to the provider-free counterfactual.  It
does not run the full benchmark and never writes the protected official v2
result.  The same frozen Phase 1 artifact, generation/judge adapters,
completion policy, and shared renderer used by Phase 2 are reused here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
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
from src.evaluation.generation_checkpoint import GenerationCheckpointStore
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V3,
    CONTEXT_STRATEGY_SELECTIVE_V4,
    render_case_context,
)
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

logger = logging.getLogger(__name__)

GEN_CHECKPOINT_PATH = Path(
    "data/eval_artifacts/context_precision_v3_sentinel_gen.jsonl"
)
JUDGE_CHECKPOINT_PATH = Path(
    "data/eval_artifacts/context_precision_v3_sentinel_judge.jsonl"
)
RESULTS_PATH = Path(
    "data/eval_artifacts/context_precision_v3_sentinel_summary.json"
)

V4_GEN_CHECKPOINT_PATH = Path(
    "data/eval_artifacts/context_precision_v4_sentinel_gen.jsonl"
)
V4_JUDGE_CHECKPOINT_PATH = Path(
    "data/eval_artifacts/context_precision_v4_sentinel_judge.jsonl"
)
V4_RESULTS_PATH = Path(
    "data/eval_artifacts/context_precision_v4_sentinel_summary.json"
)


def sentinel_artifact_paths(
    candidate_strategy: str,
    replicate_id: str | None = None,
) -> tuple[Path, Path, Path]:
    """Return isolated checkpoint/output paths for one strategy replicate."""
    if replicate_id is not None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", replicate_id):
            raise ValueError(
                "replicate_id must contain only letters, digits, '-' or '_'"
            )
        suffix = f"_{replicate_id}"
    else:
        suffix = ""
    if candidate_strategy == CONTEXT_STRATEGY_SELECTIVE_V4:
        return (
            Path(f"data/eval_artifacts/context_precision_v4_sentinel_gen{suffix}.jsonl"),
            Path(f"data/eval_artifacts/context_precision_v4_sentinel_judge{suffix}.jsonl"),
            Path(f"data/eval_artifacts/context_precision_v4_sentinel_summary{suffix}.json"),
        )
    return (
        Path(f"data/eval_artifacts/context_precision_v3_sentinel_gen{suffix}.jsonl"),
        Path(f"data/eval_artifacts/context_precision_v3_sentinel_judge{suffix}.jsonl"),
        Path(f"data/eval_artifacts/context_precision_v3_sentinel_summary{suffix}.json"),
    )

SENTINEL_QUESTIONS = (
    "Compare the cybersecurity risk disclosures of Apple, Microsoft, and Amazon.",
    "How does Microsoft describe its Azure and cloud services growth?",
    "What quality and manufacturing risks does Apple mention?",
    "What risks does Amazon face related to its international operations?",
)

REFERENCE_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")


def sentinel_cases() -> list[TestCase]:
    """Return the fixed four cases whose frozen contexts change under v3."""
    by_question = {case.question: case for case in TEST_SET}
    missing = [question for question in SENTINEL_QUESTIONS if question not in by_question]
    if missing:
        raise RuntimeError(f"Context-precision sentinel contract drift: {missing}")
    return [by_question[question] for question in SENTINEL_QUESTIONS]


def _reference_scores() -> dict[str, dict[str, float]]:
    payload = json.loads(REFERENCE_RESULTS_PATH.read_text(encoding="utf-8"))
    if (
        payload.get("official") is not True
        or payload.get("context_strategy") != "selective_packed_v2"
    ):
        raise RuntimeError(
            "Reference result is not the protected official selective-v2 run"
        )
    scores: dict[str, dict[str, float]] = {}
    for case in payload.get("cases", []):
        question = case.get("question")
        if question not in SENTINEL_QUESTIONS:
            continue
        observed = case.get("scores") or {}
        if all(isinstance(observed.get(key), (int, float)) for key in SCORE_KEYS):
            scores[question] = {
                key: float(observed[key]) for key in SCORE_KEYS
            }
    missing = [question for question in SENTINEL_QUESTIONS if question not in scores]
    if missing:
        raise RuntimeError(f"Reference v2 lacks sentinel scores: {missing}")
    return scores


def _aggregate_scores(
    scores_by_question: dict[str, dict[str, float]],
) -> dict[str, float]:
    return {
        key: round(
            sum(scores[key] for scores in scores_by_question.values())
            / max(len(scores_by_question), 1),
            4,
        )
        for key in SCORE_KEYS
    }


def _case_gates(
    summary: dict[str, Any],
    reference: dict[str, dict[str, float]],
) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    candidate_scores: dict[str, dict[str, float]] = {}
    rows: dict[str, dict[str, Any]] = {}
    for case in summary.get("cases", []):
        question = case.get("question")
        if question not in SENTINEL_QUESTIONS:
            continue
        scores = case.get("scores") or {}
        deterministic = case.get("deterministic") or {}
        score_shape = all(isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS)
        if score_shape:
            candidate_scores[question] = {
                key: float(scores[key]) for key in SCORE_KEYS
            }
        rows[question] = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": score_shape,
            "citation_correctness": deterministic.get("citation_correctness"),
            "fallback_correct": deterministic.get("fallback_correct"),
            "recall_proxy": deterministic.get("recall_proxy"),
            "reference_scores": reference.get(question),
            "candidate_scores": candidate_scores.get(question),
        }
    aggregate = (
        _aggregate_scores(candidate_scores)
        if len(candidate_scores) == len(SENTINEL_QUESTIONS)
        else {}
    )
    return rows, aggregate


def build_report(
    summary: dict[str, Any],
    reference: dict[str, dict[str, float]],
    candidate_strategy: str = CONTEXT_STRATEGY_SELECTIVE_V3,
) -> dict[str, Any]:
    """Add sentinel-specific quality gates to the shared Phase 2 summary."""
    case_rows, candidate_aggregate = _case_gates(summary, reference)
    reference_aggregate = _aggregate_scores(reference)
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
        for row in case_rows.values()
    ) and len(case_rows) == len(SENTINEL_QUESTIONS)
    score_regression_passed = all(
        candidate_aggregate.get(key, float("-inf"))
        >= reference_aggregate[key]
        for key in SCORE_KEYS
    )
    report = {
        **summary,
        "audit": (
            "context_precision_sentinel_v4"
            if candidate_strategy == CONTEXT_STRATEGY_SELECTIVE_V4
            else "context_precision_sentinel_v3"
        ),
        "official": False,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "reference_result": str(REFERENCE_RESULTS_PATH),
        "reference_aggregate": reference_aggregate,
        "candidate_aggregate": candidate_aggregate,
        "case_gates": case_rows,
        "pre_registered_gates": {
            "provider_complete": True,
            "one_shared_binding": True,
            "zero_skipped_or_failed_records": True,
            "deterministic_citation_and_fallback": True,
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


def _checkpoint_provenance(
    generation_path: Path,
    judge_path: Path,
    questions: tuple[str, ...],
    replicate_id: str,
) -> dict[str, Any]:
    """Record hashes/bindings needed to compare independent replicates."""
    generation: dict[str, dict[str, Any]] = {}
    if generation_path.exists():
        for line in generation_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            question = record.get("question")
            if question in questions and record.get("status") == "OK":
                generation[question] = record

    judging: dict[str, dict[str, Any]] = {}
    if judge_path.exists():
        for line in judge_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            question = record.get("question")
            if question in questions and record.get("status") == "OK":
                judging[question] = record

    return {
        "replicate_id": replicate_id,
        "generation_bindings": {
            question: generation[question].get("binding")
            for question in questions
            if question in generation
        },
        "generation_answer_hashes": {
            question: f"sha256:{hashlib.sha256(generation[question]['answer'].encode('utf-8')).hexdigest()}"
            for question in questions
            if question in generation
            and isinstance(generation[question].get("answer"), str)
        },
        "judge_bindings": {
            question: judging[question].get("binding")
            for question in questions
            if question in judging
        },
        "generation_checkpoint": str(generation_path),
        "judge_checkpoint": str(judge_path),
    }


def run(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    output: Path | None = None,
    fresh: bool = False,
    max_gen_retries: int = 0,
    max_judge_retries: int = 0,
    candidate_strategy: str = CONTEXT_STRATEGY_SELECTIVE_V3,
    replicate_id: str | None = None,
) -> dict[str, Any]:
    """Run the quota-gated four-case candidate and write its report."""
    assert_phase2_retrieval_hermeticity()
    default_gen, default_judge, default_output = sentinel_artifact_paths(
        candidate_strategy, replicate_id
    )
    if gen_checkpoint is None:
        gen_checkpoint = default_gen
    if judge_checkpoint is None:
        judge_checkpoint = default_judge
    if output is None:
        output = default_output
    if fresh:
        for path in (gen_checkpoint, judge_checkpoint, output):
            if path.exists():
                path.unlink()

    artifact, upstream = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        candidate_strategy,
    )
    selected = sentinel_cases()
    case_by_question = {
        case["question"]: case for case in artifact.get("cases", [])
    }
    metadata = {case.question: case for case in selected}
    missing = [case.question for case in selected if case.question not in case_by_question]
    if missing:
        raise RuntimeError(f"Artifact lacks sentinel evidence: {missing}")

    def render(case_payload: dict[str, Any]) -> str:
        question = case_payload["question"]
        return render_case_context(
            case_payload,
            required_keywords=metadata[question].required_keywords,
            strategy=candidate_strategy,
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
        gen_checkpoint,
        judge_checkpoint,
        SENTINEL_QUESTIONS,
        replicate_id or "base",
    )
    report = build_report(summary, _reference_scores(), candidate_strategy)
    report["replicate_id"] = replicate_id or "base"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--gen-checkpoint", type=Path)
    parser.add_argument("--judge-checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument(
        "--replicate-id",
        help="Optional isolated replicate suffix, e.g. r1 or r2.",
    )
    parser.add_argument(
        "--candidate-strategy",
        choices=[CONTEXT_STRATEGY_SELECTIVE_V3, CONTEXT_STRATEGY_SELECTIVE_V4],
        default=CONTEXT_STRATEGY_SELECTIVE_V3,
    )
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    args = parser.parse_args(argv)
    report = run(
        artifact_path=args.artifact,
        gen_checkpoint=args.gen_checkpoint,
        judge_checkpoint=args.judge_checkpoint,
        output=args.output,
        fresh=args.fresh,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
        candidate_strategy=args.candidate_strategy,
        replicate_id=args.replicate_id,
    )
    _, _, resolved_output = sentinel_artifact_paths(
        args.candidate_strategy, args.replicate_id
    )
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
