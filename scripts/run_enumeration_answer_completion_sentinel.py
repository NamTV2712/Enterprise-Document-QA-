"""Run the quota-gated v1 enumeration answer-completion sentinel.

This is a non-official four-case provider check for the v5 packed context plus
the unified one-correction completion policy. It writes isolated artifacts and
never replaces the promoted official benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_context_precision_sentinel import _checkpoint_provenance
from scripts.run_enumeration_context_sentinel import (
    EXPECTED_REFERENCE_SHA256,
    REFERENCE_RESULTS_PATH,
    SENTINEL_QUESTIONS,
    _aggregate,
    _reference_scores,
    sentinel_cases,
)
from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    assert_phase2_retrieval_hermeticity,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    render_case_context,
)
from src.evaluation.generation_checkpoint import GenerationCheckpointStore
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.phase2_runtime import (
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_answer_completion_postprocessor,
    make_generation_call,
    make_judge_call,
)
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.generator import Generator


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def sentinel_artifact_paths(replicate_id: str) -> tuple[Path, Path, Path]:
    if not replicate_id or not all(
        character.isalnum() or character in "-_" for character in replicate_id
    ):
        raise ValueError(
            "replicate_id must contain only letters, digits, '-' or '_'"
        )
    base = "data/eval_artifacts/enumeration_answer_completion_v1_sentinel"
    return (
        Path(f"{base}_gen_{replicate_id}.jsonl"),
        Path(f"{base}_judge_{replicate_id}.jsonl"),
        Path(f"{base}_summary_{replicate_id}.json"),
    )


def _score(case: dict[str, Any], key: str) -> float | None:
    value = (case.get("scores") or {}).get(key)
    return float(value) if isinstance(value, (int, float)) else None


def build_report(
    summary: dict[str, Any],
    reference: dict[str, dict[str, float]],
    replicate_id: str,
) -> dict[str, Any]:
    candidate = {
        case["question"]: case
        for case in summary.get("cases", [])
        if case.get("question") in SENTINEL_QUESTIONS
    }
    completion_rows = summary.get("period_value_corrections") or {}
    case_gates: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        case = candidate.get(question, {})
        row = completion_rows.get(question, {})
        deterministic = case.get("deterministic") or {}
        faithfulness = _score(case, "faithfulness")
        answer_relevancy = _score(case, "answer_relevancy")
        reference_row = reference[question]
        case_gates[question] = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": all(
                _score(case, key) is not None
                for key in ("faithfulness", "answer_relevancy", "context_precision")
            ),
            "faithfulness_floor": faithfulness is not None and faithfulness >= 0.95,
            "answer_relevancy_floor": (
                answer_relevancy is not None and answer_relevancy >= 0.90
            ),
            "semantic_drop_bounded": all(
                _score(case, key) is not None
                and _score(case, key) >= reference_row[key] - 0.10
                for key in ("faithfulness", "answer_relevancy")
            ),
            "citation_correctness": deterministic.get("citation_correctness"),
            "fallback_correct": deterministic.get("fallback_correct"),
            "unsupported_numeric_claims": len(
                row.get("final_unsupported_numeric_claims", [])
            ),
            "completion_applicable": row.get("enumeration_applicable") is True,
            "completion_final_passed": row.get("final_passed") is True,
            "completion_final_grounding": row.get("final_grounding_passed") is True,
            "completion_final_missing_empty": (
                row.get("final_missing_items") == []
            ),
            "max_one_correction": row.get("correction_attempts", 0) <= 1,
            "reference_scores": reference_row,
            "candidate_scores": case.get("scores"),
        }

    scores = {
        question: {
            key: _score(candidate[question], key)
            for key in ("faithfulness", "answer_relevancy", "context_precision")
        }
        for question in SENTINEL_QUESTIONS
        if question in candidate
        and all(_score(candidate[question], key) is not None for key in (
            "faithfulness", "answer_relevancy", "context_precision"
        ))
    }
    candidate_aggregate = _aggregate(scores) if len(scores) == 4 else {}
    reference_aggregate = _aggregate(reference)
    provider_complete = bool(
        summary.get("provider_complete")
        and summary.get("num_selected") == len(SENTINEL_QUESTIONS)
        and summary.get("num_generation_ok") == len(SENTINEL_QUESTIONS)
        and summary.get("num_judged_ok") == len(SENTINEL_QUESTIONS)
    )
    completion_passed = len(completion_rows) == len(SENTINEL_QUESTIONS) and all(
        gate["completion_applicable"]
        and gate["completion_final_passed"]
        and gate["completion_final_grounding"]
        and gate["completion_final_missing_empty"]
        and gate["max_one_correction"]
        for gate in case_gates.values()
    )
    deterministic_passed = len(case_gates) == 4 and all(
        gate["generation_ok"]
        and gate["judge_ok"]
        and gate["score_shape"]
        and gate["citation_correctness"] == 1.0
        and gate["fallback_correct"] is True
        and gate["unsupported_numeric_claims"] == 0
        for gate in case_gates.values()
    )
    semantic_passed = len(case_gates) == 4 and all(
        gate["faithfulness_floor"]
        and gate["answer_relevancy_floor"]
        and gate["semantic_drop_bounded"]
        for gate in case_gates.values()
    )
    gates = {
        "provider_complete": provider_complete,
        "deterministic_contracts": deterministic_passed,
        "completion_policy": completion_passed,
        "bounded_per_case_semantics": semantic_passed,
        "aggregate_faithfulness_floor": candidate_aggregate.get(
            "faithfulness", -1.0
        ) >= 0.95,
        "aggregate_answer_relevancy_floor": candidate_aggregate.get(
            "answer_relevancy", -1.0
        ) >= 0.90,
        "aggregate_context_precision_target": candidate_aggregate.get(
            "context_precision", -1.0
        ) >= 0.875,
    }
    return {
        **summary,
        "audit": "enumeration_answer_completion_sentinel_v1",
        "official": False,
        "replicate_id": replicate_id,
        "completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "reference_result": str(REFERENCE_RESULTS_PATH),
        "reference_result_sha256": EXPECTED_REFERENCE_SHA256,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "reference_aggregate": reference_aggregate,
        "candidate_aggregate": candidate_aggregate,
        "case_gates": case_gates,
        "pre_registered_gates": {
            "all_four_enumeration_cases_complete": True,
            "deterministic_contracts_and_final_evidence_coverage": True,
            "faithfulness_at_least_0_95_per_case_and_aggregate": True,
            "answer_relevancy_at_least_0_90_per_case_and_aggregate": True,
            "per_case_semantic_drop_no_more_than_0_10": True,
            "context_precision_at_least_0_875": True,
            "one_bounded_correction_per_answer": True,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    *,
    replicate_id: str,
    artifact_path: Path = ARTIFACT_PATH,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    output: Path | None = None,
    fresh: bool = False,
    max_gen_retries: int = 0,
    max_judge_retries: int = 0,
) -> dict[str, Any]:
    assert_phase2_retrieval_hermeticity()
    default_gen, default_judge, default_output = sentinel_artifact_paths(replicate_id)
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
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    metadata = {case.question: case for case in selected}

    def render(case_payload: dict[str, Any]) -> str:
        question = case_payload["question"]
        return render_case_context(
            case_payload,
            required_keywords=metadata[question].required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
        )

    tracker = UsageTracker()
    generation_generator = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
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
        answer_postprocessor=make_answer_completion_postprocessor(
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
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
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
        "gates": report["gates"],
        "candidate_aggregate": report["candidate_aggregate"],
        "replicate_id": args.replicate_id,
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
