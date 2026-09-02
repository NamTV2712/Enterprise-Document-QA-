"""Run one quota-gated seven-case Answer Stability sentinel.

The sentinel mixes the three known non-fact Answer Relevancy regressions with
the four fact-selector targets.  It uses the shared Phase 2 path, writes only
non-official artifacts, and accepts no checkpoint from the old completion
binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
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
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.generation_checkpoint import (
    GenerationCheckpointStore,
    parse_evidence_context,
)
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.phase2_runtime import (
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_answer_completion_postprocessor,
    make_generation_call,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.fact_context import (
    FACT_CONTEXT_SELECTOR_FINGERPRINT,
    select_fact_context,
)
from src.generation.generator import Generator


SENTINEL_QUESTIONS = (
    "What quality and manufacturing risks does Apple mention?",
    "How does Microsoft describe its Azure and cloud services growth?",
    "What are the main sources of revenue for Microsoft?",
    "What was Microsoft's total assets as of fiscal year 2025?",
    "What was Amazon's AWS net sales in 2025?",
    "Who audited Apple's financial statements and when was the report signed?",
    "Who audited Microsoft's financial statements?",
)
FACT_QUESTIONS = frozenset(SENTINEL_QUESTIONS[3:])
REGRESSION_QUESTIONS = frozenset(SENTINEL_QUESTIONS[:3])
REFERENCE_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
EXPECTED_REFERENCE_SHA256 = (
    "sha256:a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")
SEMANTIC_KEYS = ("faithfulness", "answer_relevancy")


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _checkpoint_values(path: Path, field: str) -> set[str]:
    values: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("status") == "OK" and isinstance(record.get(field), str):
            values.add(record[field])
    return values


def sentinel_artifact_paths(replicate_id: str) -> tuple[Path, Path, Path]:
    if not replicate_id or not all(
        character.isalnum() or character in "-_" for character in replicate_id
    ):
        raise ValueError(
            "replicate_id must contain only letters, digits, '-' or '_'"
        )
    base = "data/eval_artifacts/answer_stability_v1_sentinel"
    return (
        Path(f"{base}_gen_{replicate_id}.jsonl"),
        Path(f"{base}_judge_{replicate_id}.jsonl"),
        Path(f"{base}_summary_{replicate_id}.json"),
    )


def sentinel_cases() -> list[TestCase]:
    by_question = {case.question: case for case in TEST_SET}
    missing = [question for question in SENTINEL_QUESTIONS if question not in by_question]
    if missing:
        raise RuntimeError(f"Answer stability sentinel contract drift: {missing}")
    cases = [by_question[question] for question in SENTINEL_QUESTIONS]
    if any(case.category not in {"summary", "enumeration", "fact_lookup"} for case in cases):
        raise RuntimeError("Answer stability sentinel contains an unsupported category")
    return cases


def _reference_scores() -> dict[str, dict[str, float]]:
    if _file_sha256(REFERENCE_RESULTS_PATH) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("Promoted official reference SHA-256 drift")
    payload = json.loads(REFERENCE_RESULTS_PATH.read_text(encoding="utf-8"))
    if payload.get("official") is not True:
        raise RuntimeError("Reference result is not official")
    scores: dict[str, dict[str, float]] = {}
    for case in payload.get("cases", []):
        question = case.get("question")
        observed = case.get("scores") or {}
        if question in SENTINEL_QUESTIONS and all(
            isinstance(observed.get(key), (int, float)) for key in SCORE_KEYS
        ):
            scores[question] = {
                key: float(observed[key]) for key in SCORE_KEYS
            }
    missing = set(SENTINEL_QUESTIONS) - set(scores)
    if missing:
        raise RuntimeError(f"Official reference lacks sentinel scores: {missing}")
    return scores


def _aggregate(scores: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        key: round(
            sum(row[key] for row in scores.values()) / max(len(scores), 1),
            4,
        )
        for key in SCORE_KEYS
    }


def _selector_rows(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_question = {case["question"]: case for case in artifact["cases"]}
    rows: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        payload = by_question[question]
        v5 = render_case_context(payload, strategy=CONTEXT_STRATEGY_SELECTIVE_V5)
        v6 = render_case_context(payload, strategy=CONTEXT_STRATEGY_SELECTIVE_V6)
        row: dict[str, Any] = {
            "v5_context_sha256": _sha256_text(v5),
            "v6_context_sha256": _sha256_text(v6),
            "v5_v6_context_identical": v5 == v6,
            "v6_source_count": len(parse_evidence_context(v6)),
        }
        if question in FACT_QUESTIONS:
            selection = select_fact_context(payload)
            row.update(
                {
                    "selector_tier": selection.tier,
                    "selected_chunk_ids": list(selection.kept_ids),
                    "selector_safe": selection.safe,
                    "selector_one_source": row["v6_source_count"] == 1,
                }
            )
        else:
            row.update(
                {
                    "selector_tier": "inherited_selective_v5",
                    "selected_chunk_ids": [],
                    "selector_safe": True,
                    "selector_one_source": True,
                }
            )
        rows[question] = row
    return rows


def build_report(
    summary: dict[str, Any],
    reference: dict[str, dict[str, float]],
    selector_rows: dict[str, dict[str, Any]],
    replicate_id: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    candidates = {
        case["question"]: case
        for case in summary.get("cases", [])
        if case.get("question") in SENTINEL_QUESTIONS
    }
    completion_rows = summary.get("period_value_corrections") or {}
    case_gates: dict[str, dict[str, Any]] = {}
    candidate_scores: dict[str, dict[str, float]] = {}
    for question in SENTINEL_QUESTIONS:
        case = candidates.get(question, {})
        scores = case.get("scores") or {}
        if all(isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS):
            candidate_scores[question] = {
                key: float(scores[key]) for key in SCORE_KEYS
            }
        selector = selector_rows.get(question, {})
        completion = completion_rows.get(question, {})
        deterministic = case.get("deterministic") or {}
        answer = case.get("answer") or ""
        source_texts = [
            block["text"]
            for block in parse_evidence_context(
                render_case_context(
                    next(
                        payload
                        for payload in artifact["cases"]
                        if payload["question"] == question
                    ),
                    strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
                )
            )
        ]
        answer_audit = audit_answer(answer, source_texts)
        faithfulness = scores.get("faithfulness")
        answer_relevancy = scores.get("answer_relevancy")
        stability_required = question == (
            "How does Microsoft describe its Azure and cloud services growth?"
        )
        case_gates[question] = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": all(
                isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS
            ),
            "faithfulness_exact_one": faithfulness == 1.0,
            "answer_relevancy_floor": (
                isinstance(answer_relevancy, (int, float))
                and answer_relevancy >= 0.95
            ),
            "semantic_drop_bounded": all(
                isinstance(scores.get(key), (int, float))
                and scores[key] >= reference[question][key] - 0.10
                for key in SEMANTIC_KEYS
            ),
            "citation_correctness": deterministic.get("citation_correctness"),
            "recall_proxy": deterministic.get("recall_proxy"),
            "fallback_correct": deterministic.get("fallback_correct"),
            "answer_integrity": not (
                answer_audit.uncited_answer
                or answer_audit.malformed_line_citations
                or answer_audit.out_of_range_citations
                or answer_audit.unsupported_numeric_claims
                or answer_audit.fallback_answer
            ),
            "unsupported_numeric_claims": completion.get(
                "final_unsupported_numeric_claims", []
            ),
            "completion_policy": (
                completion.get("applicable") is not True
                or (
                    completion.get("final_passed") is True
                    and completion.get("final_grounding_passed") is True
                )
            ),
            "stability_canary": (
                not stability_required
                or (
                    completion.get("stability_applicable") is True
                    and completion.get("final_stability_passed") is True
                    and completion.get("stability_missing_facts") == []
                )
            ),
            "context_identity": (
                question in REGRESSION_QUESTIONS
                and selector.get("v5_v6_context_identical") is True
            )
            or question in FACT_QUESTIONS,
            "selector_safe": selector.get("selector_safe") is True,
            "selector_one_source": selector.get("selector_one_source") is True,
            "selector_tier": selector.get("selector_tier"),
            "reference_scores": reference[question],
            "candidate_scores": scores,
        }

    provider_complete = bool(
        summary.get("provider_complete")
        and summary.get("official") is False
        and summary.get("context_strategy") == CONTEXT_STRATEGY_SELECTIVE_V6
        and summary.get("num_selected") == len(SENTINEL_QUESTIONS)
        and summary.get("num_generation_ok") == len(SENTINEL_QUESTIONS)
        and summary.get("num_judged_ok") == len(SENTINEL_QUESTIONS)
    )
    deterministic_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        gate["generation_ok"]
        and gate["judge_ok"]
        and gate["score_shape"]
        and gate["citation_correctness"] == 1.0
        and gate["recall_proxy"] == 1.0
        and gate["fallback_correct"] is True
        and gate["answer_integrity"]
        and not gate["unsupported_numeric_claims"]
        for gate in case_gates.values()
    )
    semantic_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        gate["faithfulness_exact_one"]
        and gate["answer_relevancy_floor"]
        and gate["semantic_drop_bounded"]
        for gate in case_gates.values()
    )
    completion_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        gate["completion_policy"] and gate["stability_canary"]
        for gate in case_gates.values()
    )
    selector_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        gate["context_identity"]
        and gate["selector_safe"]
        and gate["selector_one_source"]
        for gate in case_gates.values()
    )
    candidate_aggregate = (
        _aggregate(candidate_scores)
        if len(candidate_scores) == len(SENTINEL_QUESTIONS)
        else {}
    )
    gates = {
        "provider_complete": provider_complete,
        "single_binding": bool(summary.get("binding")),
        "selector_and_context_contract": selector_passed,
        "deterministic_contracts": deterministic_passed,
        "completion_and_stability_contract": completion_passed,
        "semantic_contract": semantic_passed,
        "aggregate_faithfulness_exact_one": candidate_aggregate.get(
            "faithfulness", -1.0
        ) == 1.0,
        "aggregate_answer_relevancy_floor": candidate_aggregate.get(
            "answer_relevancy", -1.0
        ) >= 0.95,
    }
    return {
        **summary,
        "audit": "answer_stability_sentinel_v1",
        "official": False,
        "replicate_id": replicate_id,
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "reference_scores": reference,
        "reference_aggregate": _aggregate(reference),
        "candidate_aggregate": candidate_aggregate,
        "selector_rows": selector_rows,
        "case_gates": case_gates,
        "pre_registered_gates": {
            "seven_cases_complete": True,
            "regression_contexts_byte_identical": True,
            "fact_targets_safe_single_source": True,
            "faithfulness_exactly_1_0": True,
            "answer_relevancy_at_least_0_95": True,
            "semantic_drop_no_more_than_0_10": True,
            "deterministic_grounding_contracts": True,
            "azure_numeric_stability_canary": True,
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
        CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    selected = sentinel_cases()
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    metadata = {case.question: case for case in selected}
    selector_rows = _selector_rows(artifact)

    def render(case_payload: dict[str, Any]) -> str:
        question = case_payload["question"]
        return render_case_context(
            case_payload,
            required_keywords=metadata[question].required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )

    tracker = UsageTracker()
    generation_generator = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
    judge_generator = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    generation_call = make_generation_call(generation_generator, tracker)
    completion_rows: dict[str, dict[str, Any]] = {}
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
            generation_call, completion_rows
        ),
        answer_completion_metadata=completion_rows,
        publish_official=False,
    )
    summary["token_usage_totals"] = tracker.totals
    report = build_report(
        summary,
        _reference_scores(),
        selector_rows,
        replicate_id,
        artifact,
    )
    generation_bindings = _checkpoint_values(gen_checkpoint, "binding")
    judge_bindings = _checkpoint_values(judge_checkpoint, "binding")
    report["replicate_provenance"] = {
        "generation_checkpoint": str(gen_checkpoint),
        "generation_checkpoint_sha256": _file_sha256(gen_checkpoint),
        "judge_checkpoint": str(judge_checkpoint),
        "judge_checkpoint_sha256": _file_sha256(judge_checkpoint),
        "generation_binding_values": sorted(generation_bindings),
        "judge_binding_values": sorted(judge_bindings),
        "one_generation_binding": generation_bindings == {summary.get("binding")},
        "one_judge_binding": judge_bindings == {summary.get("binding")},
        "generation_records": len(
            [value for value in gen_checkpoint.read_text(encoding="utf-8").splitlines() if value.strip()]
        ),
        "judge_records": len(
            [value for value in judge_checkpoint.read_text(encoding="utf-8").splitlines() if value.strip()]
        ),
    }
    if output is None:
        raise RuntimeError("Sentinel output path is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
