"""Run one provider-gated sentinel for Comparative Answerability Guard v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    JUDGE_CHECKPOINT_PATH,
    assert_phase2_retrieval_hermeticity,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.answer_contract import audit_answer
from src.evaluation.answer_postprocessor_profile import (
    build_answer_postprocessor_profile,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.generation_checkpoint import (
    GenerationCheckpointStore,
    parse_evidence_context,
)
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.phase2_runtime import (
    JUDGE_CONTEXT_BUILDER_FINGERPRINT,
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_answer_completion_postprocessor,
    make_generation_call,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_FINGERPRINT,
    assess_comparative_answerability,
)
from src.generation.period_value_completeness import FALLBACK_ANSWER
from src.generation.generator import Generator


ARTIFACT_PATH = Path(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json"
)
REFERENCE_PATH = Path("data/eval_artifacts/phase2_results_packed_selective_v2.json")
EXPECTED_REFERENCE_SHA256 = (
    "sha256:a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
SENTINEL_QUESTIONS = (
    "Which company depends more on cloud/subscription revenue, Microsoft or Apple?",
    "What are all the major risk factors Microsoft discloses?",
    "How does Amazon's AWS segment compare to Microsoft's cloud business in terms of growth?",
    "Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?",
    "Compare Apple's and Amazon's approach to international operations risk.",
    "What are Disney's main risk factors?",
)
TARGET_QUESTION = SENTINEL_QUESTIONS[0]
RISK_CONTROL_QUESTION = SENTINEL_QUESTIONS[1]
OUT_OF_CORPUS_QUESTION = SENTINEL_QUESTIONS[5]
COMPARATIVE_QUESTIONS = frozenset(SENTINEL_QUESTIONS[:5])
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _checkpoint_bindings(path: Path, field: str) -> set[str]:
    values: set[str] = set()
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("status") == "OK" and isinstance(record.get(field), str):
            values.add(record[field])
    return values


def _reference_scores() -> dict[str, dict[str, float]]:
    if _file_sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("Protected official reference SHA-256 drifted")
    payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    scores: dict[str, dict[str, float]] = {}
    for case in payload.get("cases", []):
        if case.get("question") not in SENTINEL_QUESTIONS:
            continue
        observed = case.get("scores") or {}
        if all(isinstance(observed.get(key), (int, float)) for key in SCORE_KEYS):
            scores[case["question"]] = {
                key: float(observed[key]) for key in SCORE_KEYS
            }
    missing = set(SENTINEL_QUESTIONS) - set(scores)
    if missing:
        raise RuntimeError(f"Official reference lacks sentinel scores: {sorted(missing)}")
    return scores


def _sentinel_cases() -> list[Any]:
    by_question = {case.question: case for case in TEST_SET}
    missing = [question for question in SENTINEL_QUESTIONS if question not in by_question]
    if missing:
        raise RuntimeError(f"Sentinel questions absent from TEST_SET: {missing}")
    return [by_question[question] for question in SENTINEL_QUESTIONS]


def _context_rows(
    artifact: dict[str, Any],
    cases: list[Any],
) -> dict[str, dict[str, Any]]:
    by_question = {case["question"]: case for case in artifact["cases"]}
    rows: dict[str, dict[str, Any]] = {}
    for test_case in cases:
        payload = by_question[test_case.question]
        context = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        repeat = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        rows[test_case.question] = {
            "context": context,
            "context_sha256": _text_sha256(context),
            "source_count": len(parse_evidence_context(context)),
            "context_deterministic": context == repeat,
        }
    return rows


def _case_gates(
    summary: dict[str, Any],
    artifact: dict[str, Any],
    reference: dict[str, dict[str, float]],
    contexts: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    candidates = {case["question"]: case for case in summary.get("cases", [])}
    completions = summary.get("period_value_corrections") or {}
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}
    by_test_case = {case.question: case for case in _sentinel_cases()}
    result: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        case = candidates.get(question, {})
        scores = case.get("scores") or {}
        answer = case.get("answer") or ""
        completion = completions.get(question) or {}
        source_texts = [
            source["text"]
            for source in parse_evidence_context(contexts[question]["context"])
        ]
        audit = audit_answer(answer, source_texts)
        score_shape = all(isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS)
        common = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": score_shape,
            "faithfulness_exact_one": scores.get("faithfulness") == 1.0,
            "citation_integrity": not (
                audit.uncited_answer
                or audit.malformed_line_citations
                or audit.out_of_range_citations
                or audit.unsupported_numeric_claims
            ),
            "completion_final_passed": completion.get("final_passed") is True,
            "completion_final_grounding_passed": (
                completion.get("final_grounding_passed") is True
                or (
                    by_test_case[question].expects_fallback
                    and audit.fallback_answer
                )
            ),
            "max_one_correction": completion.get("correction_attempts", 0) <= 1,
            "context_deterministic": contexts[question]["context_deterministic"],
            "context_source_count_positive": contexts[question]["source_count"] > 0,
        }
        if question == TARGET_QUESTION:
            common.update(
                {
                    "target_non_fallback": not audit.fallback_answer,
                    "target_answer_relevancy_exact_one": (
                        scores.get("answer_relevancy") == 1.0
                    ),
                    "answerability_applicable": (
                        completion.get("answerability_applicable") is True
                    ),
                    "answerability_evidence_sufficient": (
                        completion.get("answerability_evidence_sufficient") is True
                    ),
                    "answerability_reason_recorded": (
                        not completion.get("correction_attempted")
                        or (
                            completion.get("final_passed") is True
                            and completion.get("final_grounding_passed") is True
                            and completion.get("answerability_applicable") is True
                            and completion.get(
                                "answerability_evidence_sufficient"
                            ) is True
                        )
                    ),
                }
            )
        elif question == RISK_CONTROL_QUESTION:
            common.update(
                {
                    "risk_faithfulness_exact_one": scores.get("faithfulness") == 1.0,
                    "risk_answer_relevancy_floor": (
                        isinstance(scores.get("answer_relevancy"), (int, float))
                        and scores["answer_relevancy"] >= 0.95
                    ),
                    "answerability_not_applicable": (
                        completion.get("answerability_applicable") is False
                    ),
                }
            )
        elif question == OUT_OF_CORPUS_QUESTION:
            common.update(
                {
                    "fallback_correct": audit.fallback_answer,
                    "answerability_not_applicable": (
                        completion.get("answerability_applicable") is False
                    ),
                }
            )
        else:
            common.update(
                {
                    "comparative_non_fallback": not audit.fallback_answer,
                    "answer_relevancy_drop_bounded": (
                        isinstance(scores.get("answer_relevancy"), (int, float))
                        and scores["answer_relevancy"]
                        >= reference[question]["answer_relevancy"] - 0.05
                    ),
                    "answerability_applicable": (
                        completion.get("answerability_applicable") is True
                    ),
                    "answerability_evidence_sufficient": (
                        completion.get("answerability_evidence_sufficient") is True
                    ),
                }
            )
        result[question] = common
    return result


def build_report(
    summary: dict[str, Any],
    artifact: dict[str, Any],
    reference: dict[str, dict[str, float]],
    generation_checkpoint: Path,
    judge_checkpoint: Path,
    replicate_id: str,
) -> dict[str, Any]:
    contexts = _context_rows(artifact, _sentinel_cases())
    case_gates = _case_gates(summary, artifact, reference, contexts)
    common_required = (
        "generation_ok",
        "judge_ok",
        "score_shape",
        "faithfulness_exact_one",
        "citation_integrity",
        "completion_final_passed",
        "completion_final_grounding_passed",
        "max_one_correction",
        "context_deterministic",
        "context_source_count_positive",
    )
    case_passed: dict[str, bool] = {}
    for question, row in case_gates.items():
        required = list(common_required)
        if question == TARGET_QUESTION:
            required += [
                "target_non_fallback",
                "target_answer_relevancy_exact_one",
                "answerability_applicable",
                "answerability_evidence_sufficient",
                "answerability_reason_recorded",
            ]
        elif question == RISK_CONTROL_QUESTION:
            required += [
                "risk_faithfulness_exact_one",
                "risk_answer_relevancy_floor",
                "answerability_not_applicable",
            ]
        elif question == OUT_OF_CORPUS_QUESTION:
            required += ["fallback_correct", "answerability_not_applicable"]
        else:
            required += [
                "comparative_non_fallback",
                "answer_relevancy_drop_bounded",
                "answerability_applicable",
                "answerability_evidence_sufficient",
            ]
        row["required_gates"] = required
        row["passed"] = all(row.get(key) is True for key in required)
        case_passed[question] = row["passed"]

    generation_bindings = _checkpoint_bindings(generation_checkpoint, "binding")
    judge_contexts = _checkpoint_bindings(judge_checkpoint, "judge_context_fingerprint")
    provider_complete = (
        summary.get("provider_complete") is True
        and summary.get("num_selected") == len(SENTINEL_QUESTIONS)
        and summary.get("num_generation_ok") == len(SENTINEL_QUESTIONS)
        and summary.get("num_judged_ok") == len(SENTINEL_QUESTIONS)
        and not summary.get("stopped_reason")
    )
    aggregate = summary.get("metrics") or {}
    gates = {
        "provider_complete": provider_complete,
        "single_generation_binding": generation_bindings == {summary.get("binding")},
        "single_judge_context_fingerprint": judge_contexts == {
            JUDGE_CONTEXT_BUILDER_FINGERPRINT
        },
        "all_case_gates": len(case_passed) == len(SENTINEL_QUESTIONS)
        and all(case_passed.values()),
        "aggregate_faithfulness_exact_one": aggregate.get("faithfulness") == 1.0,
        "aggregate_answer_relevancy_floor": (
            isinstance(aggregate.get("answer_relevancy"), (int, float))
            and aggregate["answer_relevancy"] >= 0.95
        ),
        "aggregate_context_precision_floor": (
            isinstance(aggregate.get("context_precision"), (int, float))
            and aggregate["context_precision"] >= 0.67
        ),
    }
    return {
        **summary,
        "schema_version": 1,
        "audit": "comparative_answerability_stability_v1_sentinel",
        "official": False,
        "replicate_id": replicate_id,
        "reference_sha256": EXPECTED_REFERENCE_SHA256,
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_FINGERPRINT,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "reference_scores": reference,
        "context_rows": {
            question: {
                key: value
                for key, value in row.items()
                if key != "context"
            }
            for question, row in contexts.items()
        },
        "case_gates": case_gates,
        "case_passed": case_passed,
        "checkpoint_provenance": {
            "generation_checkpoint": str(generation_checkpoint),
            "judge_checkpoint": str(judge_checkpoint),
            "generation_bindings": sorted(generation_bindings),
            "judge_context_fingerprints": sorted(judge_contexts),
            "one_generation_binding": len(generation_bindings) == 1,
            "one_judge_context_fingerprint": len(judge_contexts) == 1,
        },
        "pre_registered_gates": {
            "minimum_replicates": 2,
            "best_of_selection_forbidden": True,
            "target_faithfulness_and_answer_relevancy_exact_one": True,
            "risk_control_answer_relevancy_at_least_0_95": True,
            "out_of_corpus_fallback_preserved": True,
            "correction_attempts_at_most_one": True,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    *,
    replicate_id: str,
    artifact_path: Path = ARTIFACT_PATH,
    generation_checkpoint: Path,
    judge_checkpoint: Path,
    output: Path,
    fresh: bool = False,
) -> dict[str, Any]:
    assert_phase2_retrieval_hermeticity()
    if not replicate_id or not all(
        character.isalnum() or character in "-_" for character in replicate_id
    ):
        raise ValueError("replicate_id must contain only letters, digits, '-' or '_'")
    if fresh:
        for path in (generation_checkpoint, judge_checkpoint, output):
            path.unlink(missing_ok=True)

    cases = _sentinel_cases()
    artifact, upstream = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V7,
        build_answer_postprocessor_profile(),
    )
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    tracker = UsageTracker()
    generation_generator = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
    judge_generator = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    generation_call = make_generation_call(generation_generator, tracker)
    completion_rows: dict[str, dict[str, Any]] = {}
    postprocessor = make_answer_completion_postprocessor(
        generation_call, completion_rows
    )
    context_rows = _context_rows(artifact, cases)

    def context_fn(case_payload: dict[str, Any]) -> str:
        return context_rows[case_payload["question"]]["context"]

    summary = run_phase2(
        selected=cases,
        case_by_question=case_by_question,
        upstream=upstream,
        bound_fingerprint=EXPECTED_ARTIFACT_FINGERPRINT,
        generate_fn=generation_call,
        judge_fn=make_judge_call(judge_generator, tracker),
        generation_store=GenerationCheckpointStore(generation_checkpoint),
        judge_store=JudgeCheckpointStore(judge_checkpoint),
        max_gen_retries=0,
        max_judge_retries=0,
        evidence_context_fn=context_fn,
        answer_postprocessor=postprocessor,
        answer_completion_metadata=completion_rows,
        publish_official=False,
        force_non_official=True,
    )
    summary["token_usage_totals"] = tracker.totals
    report = build_report(
        summary,
        artifact,
        _reference_scores(),
        generation_checkpoint,
        judge_checkpoint,
        replicate_id,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replicate-id", required=True)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--generation-checkpoint", type=Path, required=True)
    parser.add_argument("--judge-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    report = run(
        replicate_id=args.replicate_id,
        artifact_path=args.artifact,
        generation_checkpoint=args.generation_checkpoint,
        judge_checkpoint=args.judge_checkpoint,
        output=args.output,
        fresh=args.fresh,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
