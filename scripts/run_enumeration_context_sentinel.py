"""Run one four-case enumeration-context provider sentinel replicate.

The run is non-official, uses isolated checkpoints, and compares all priority
<=2 enumeration cases with the promoted selective-v2 reference. A replicate
passes only when provider coverage, deterministic contracts, per-case
semantic non-regression, and aggregate Context Precision improvement all pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_context_precision_sentinel import _checkpoint_provenance
from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    assert_phase2_retrieval_hermeticity,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V5,
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


REFERENCE_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
EXPECTED_REFERENCE_SHA256 = (
    "sha256:db121babe17ac213222dead90a476e03a2fa256007f0335deac01ff1ff8fc648"
)
SENTINEL_QUESTIONS = tuple(
    case.question
    for case in TEST_SET
    if case.priority <= 2 and case.category == "enumeration"
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")
SEMANTIC_KEYS = ("faithfulness", "answer_relevancy")


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def sentinel_artifact_paths(replicate_id: str) -> tuple[Path, Path, Path]:
    if not replicate_id or not all(
        character.isalnum() or character in "-_" for character in replicate_id
    ):
        raise ValueError(
            "replicate_id must contain only letters, digits, '-' or '_'"
        )
    base = "data/eval_artifacts/enumeration_context_v1_sentinel"
    return (
        Path(f"{base}_gen_{replicate_id}.jsonl"),
        Path(f"{base}_judge_{replicate_id}.jsonl"),
        Path(f"{base}_summary_{replicate_id}.json"),
    )


def sentinel_cases() -> list[TestCase]:
    by_question = {case.question: case for case in TEST_SET}
    return [by_question[question] for question in SENTINEL_QUESTIONS]


def _reference_scores() -> dict[str, dict[str, float]]:
    if _file_sha256(REFERENCE_RESULTS_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("Promoted official reference SHA-256 drift")
    payload = json.loads(REFERENCE_RESULTS_PATH.read_text(encoding="utf-8"))
    if (
        payload.get("official") is not True
        or payload.get("context_strategy") != CONTEXT_STRATEGY_SELECTIVE_V2
    ):
        raise RuntimeError("Reference is not the promoted official v2 result")
    scores = {
        case.get("question"): {
            key: float(case.get("scores", {})[key]) for key in SCORE_KEYS
        }
        for case in payload.get("cases", [])
        if case.get("question") in SENTINEL_QUESTIONS
        and all(
            isinstance(case.get("scores", {}).get(key), (int, float))
            for key in SCORE_KEYS
        )
    }
    missing = set(SENTINEL_QUESTIONS) - set(scores)
    if missing:
        raise RuntimeError(f"Official reference lacks sentinel scores: {missing}")
    return scores


def _aggregate(scores: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        key: round(sum(row[key] for row in scores.values()) / len(scores), 4)
        for key in SCORE_KEYS
    }


def build_report(
    summary: dict[str, Any],
    reference: dict[str, dict[str, float]],
    replicate_id: str,
) -> dict[str, Any]:
    candidate: dict[str, dict[str, float]] = {}
    case_gates: dict[str, dict[str, Any]] = {}
    for case in summary.get("cases", []):
        question = case.get("question")
        if question not in SENTINEL_QUESTIONS:
            continue
        scores = case.get("scores") or {}
        deterministic = case.get("deterministic") or {}
        score_shape = all(
            isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS
        )
        if score_shape:
            candidate[question] = {
                key: float(scores[key]) for key in SCORE_KEYS
            }
        semantic_non_regression = bool(
            score_shape
            and all(
                candidate[question][key] >= reference[question][key]
                for key in SEMANTIC_KEYS
            )
        )
        case_gates[question] = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": score_shape,
            "citation_correctness": deterministic.get("citation_correctness"),
            "fallback_correct": deterministic.get("fallback_correct"),
            "recall_proxy": deterministic.get("recall_proxy"),
            "semantic_non_regression": semantic_non_regression,
            "reference_scores": reference[question],
            "candidate_scores": candidate.get(question),
        }

    reference_aggregate = _aggregate(reference)
    candidate_aggregate = (
        _aggregate(candidate)
        if len(candidate) == len(SENTINEL_QUESTIONS)
        else {}
    )
    completion_rows = summary.get("period_value_corrections") or {}
    completion_passed = set(completion_rows) == set(SENTINEL_QUESTIONS) and all(
        isinstance(completion_rows.get(question), dict)
        and completion_rows[question].get("applicable") is False
        and completion_rows[question].get("correction_attempted") is False
        and completion_rows[question].get("final_passed") is True
        and completion_rows[question].get("final_grounding_passed") is True
        for question in SENTINEL_QUESTIONS
    )
    provider_complete = bool(
        summary.get("provider_complete")
        and summary.get("num_selected") == len(SENTINEL_QUESTIONS)
        and summary.get("num_generation_ok") == len(SENTINEL_QUESTIONS)
        and summary.get("num_judged_ok") == len(SENTINEL_QUESTIONS)
    )
    deterministic_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        row["generation_ok"]
        and row["judge_ok"]
        and row["citation_correctness"] == 1.0
        and row["fallback_correct"] is True
        and row["recall_proxy"] is not False
        for row in case_gates.values()
    )
    semantic_non_regression = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        row["semantic_non_regression"] for row in case_gates.values()
    )
    aggregate_non_regression = all(
        candidate_aggregate.get(key, float("-inf")) >= reference_aggregate[key]
        for key in SEMANTIC_KEYS
    )
    context_precision_improved = (
        candidate_aggregate.get("context_precision", float("-inf"))
        > reference_aggregate["context_precision"]
    )
    gates = {
        "provider_complete": provider_complete,
        "deterministic_contracts": deterministic_passed,
        "completion_policy": completion_passed,
        "per_case_semantic_non_regression": semantic_non_regression,
        "aggregate_semantic_non_regression": aggregate_non_regression,
        "aggregate_context_precision_strict_improvement": context_precision_improved,
    }
    report = {
        **summary,
        "audit": "enumeration_context_sentinel_v1",
        "official": False,
        "replicate_id": replicate_id,
        "completion_fingerprint": PERIOD_VALUE_CORRECTION_FINGERPRINT,
        "reference_result": str(REFERENCE_RESULTS_PATH),
        "reference_result_sha256": EXPECTED_REFERENCE_SHA256,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "reference_aggregate": reference_aggregate,
        "candidate_aggregate": candidate_aggregate,
        "case_gates": case_gates,
        "pre_registered_gates": {
            "all_four_enumeration_cases_complete": True,
            "deterministic_and_completion_contracts": True,
            "no_per_case_faithfulness_or_answer_relevancy_regression": True,
            "aggregate_faithfulness_and_answer_relevancy_not_below_official": True,
            "aggregate_context_precision_strictly_above_official": True,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }
    return report


def run(
    *,
    replicate_id: str,
    artifact_path: Path = ARTIFACT_PATH,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    output: Path | None = None,
    fresh: bool = False,
    max_gen_retries: int = 2,
    max_judge_retries: int = 2,
) -> dict[str, Any]:
    assert_phase2_retrieval_hermeticity()
    default_gen, default_judge, default_output = sentinel_artifact_paths(
        replicate_id
    )
    gen_checkpoint = gen_checkpoint or default_gen
    judge_checkpoint = judge_checkpoint or default_judge
    output = output or default_output
    if fresh:
        for path in (gen_checkpoint, judge_checkpoint, output):
            path.unlink(missing_ok=True)

    artifact, upstream = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V5,
    )
    selected = sentinel_cases()
    case_by_question = {
        case["question"]: case for case in artifact.get("cases", [])
    }
    metadata = {case.question: case for case in selected}

    def render(case_payload: dict[str, Any]) -> str:
        question = case_payload["question"]
        return render_case_context(
            case_payload,
            required_keywords=metadata[question].required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
        )

    tracker = UsageTracker()
    generation_generator = Generator(
        model=EVAL_MODEL, api_keys=generation_pool_keys()
    )
    judge_generator = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
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
        replicate_id,
    )
    report = build_report(summary, _reference_scores(), replicate_id)
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
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=2)
    parser.add_argument("--max-judge-retries", type=int, default=2)
    args = parser.parse_args(argv)
    report = run(
        replicate_id=args.replicate_id,
        artifact_path=args.artifact,
        gen_checkpoint=args.gen_checkpoint,
        judge_checkpoint=args.judge_checkpoint,
        output=args.output,
        fresh=args.fresh,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
    )
    print(json.dumps({
        "passed": report["passed"],
        "provider_complete": report["gates"]["provider_complete"],
        "candidate_aggregate": report["candidate_aggregate"],
        "reference_aggregate": report["reference_aggregate"],
        "gates": report["gates"],
        "replicate_id": args.replicate_id,
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
