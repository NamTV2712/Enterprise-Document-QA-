"""Run one quota-gated P3 fact-evidence v2 sentinel replicate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    EVAL_MODEL,
    assert_phase2_retrieval_hermeticity,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.answer_contract import audit_answer
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
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_answer_completion_postprocessor,
    make_generation_call,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.fact_context import (
    FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
    select_fact_context_v2,
)
from src.generation.generator import Generator


ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority3_shadow_v1.json")
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:98cb84d80987642f1272f49fa7fd0040237cd34d4fc9b82a7409bb6a248fdf97"
)
REFERENCE_JUDGE_PATH = Path(
    "data/eval_artifacts/phase2_judge_priority3_shadow_v1.jsonl"
)
EXPECTED_REFERENCE_JUDGE_SHA256 = (
    "sha256:e90669509c98b3a7952f129ebb3daffb19867a6935f875c5f654f1e9e3bddc84"
    .replace(" ", "")
)
SENTINEL_QUESTIONS = (
    "What was Visa's total assets in fiscal year 2025?",
    "What was Mastercard's total assets in fiscal year 2025?",
    "What was Eli Lilly's total assets in fiscal year 2025?",
    "What were Chevron's total assets in fiscal years 2025 and 2024?",
    "What were JPMorgan Chase's total assets in fiscal years 2025 and 2024?",
    "What were ExxonMobil's total assets in fiscal years 2025 and 2024?",
    "What was IBM's total revenue in fiscal year 2025?",
    "What was IBM's net income in fiscal year 2025?",
    "What were IBM's total assets in fiscal years 2025 and 2024?",
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")
SAFE_TIERS = {"structured_exact", "exact_phrase", "full_terms"}


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _checkpoint_values(path: Path, field: str) -> set[str]:
    values: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        value = row.get(field)
        if row.get("status") == "OK" and isinstance(value, str):
            values.add(value)
    return values


def _checkpoint_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sentinel_artifact_paths(replicate_id: str) -> tuple[Path, Path, Path, Path]:
    if not replicate_id or not all(
        character.isalnum() or character in "-_" for character in replicate_id
    ):
        raise ValueError("replicate_id must contain only letters, digits, '-' or '_'")
    base = "data/eval_artifacts/priority3_fact_v2_sentinel"
    return (
        Path(f"{base}_gen_{replicate_id}.jsonl"),
        Path(f"{base}_judge_{replicate_id}.jsonl"),
        Path(f"{base}_summary_{replicate_id}.json"),
        Path(f"data/diagnostics/priority3_fact_v2_sentinel_{replicate_id}.json"),
    )


def sentinel_cases() -> list[TestCase]:
    by_question = {case.question: case for case in TEST_SET}
    missing = [question for question in SENTINEL_QUESTIONS if question not in by_question]
    if missing:
        raise RuntimeError(f"P3 fact sentinel contract drift: {missing}")
    cases = [by_question[question] for question in SENTINEL_QUESTIONS]
    if any(case.category != "fact_lookup" or case.priority != 3 for case in cases):
        raise RuntimeError("P3 fact sentinel contains a non-P3 fact case")
    return cases


def _reference_scores() -> dict[str, dict[str, float]]:
    if _sha256(REFERENCE_JUDGE_PATH) != EXPECTED_REFERENCE_JUDGE_SHA256:
        raise RuntimeError("P3 baseline judge checkpoint SHA-256 drift")
    scores: dict[str, dict[str, float]] = {}
    for row in _checkpoint_records(REFERENCE_JUDGE_PATH):
        if row.get("question") not in SENTINEL_QUESTIONS:
            continue
        observed = row.get("scores") or {}
        if row.get("status") == "OK" and all(
            isinstance(observed.get(key), (int, float)) for key in SCORE_KEYS
        ):
            scores[row["question"]] = {
                key: float(observed[key]) for key in SCORE_KEYS
            }
    if set(scores) != set(SENTINEL_QUESTIONS):
        raise RuntimeError("P3 baseline lacks complete fact reference scores")
    return scores


def _selector_rows(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_question = {case["question"]: case for case in artifact["cases"]}
    rows: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        case = by_question[question]
        selection = select_fact_context_v2(case)
        context = render_case_context(case, strategy=CONTEXT_STRATEGY_SELECTIVE_V7)
        rows[question] = {
            "selector_tier": selection.tier,
            "selected_chunk_ids": list(selection.kept_ids),
            "source_count": len(parse_evidence_context(context)),
            "context_sha256": _sha256_text(context),
            "safe": selection.safe,
        }
    return rows


def _aggregate(scores: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        key: round(
            sum(row[key] for row in scores.values()) / max(len(scores), 1),
            4,
        )
        for key in SCORE_KEYS
    }


def build_report(
    summary: dict[str, Any],
    reference: dict[str, dict[str, float]],
    selector_rows: dict[str, dict[str, Any]],
    replicate_id: str,
    generation_path: Path,
    judge_path: Path,
    artifact_cases: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidates = {
        case["question"]: case
        for case in summary.get("cases", [])
        if case.get("question") in SENTINEL_QUESTIONS
    }
    completion_rows = summary.get("period_value_corrections") or {}
    candidate_scores: dict[str, dict[str, float]] = {}
    case_gates: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        case = candidates.get(question, {})
        scores = case.get("scores") or {}
        if all(isinstance(scores.get(key), (int, float)) for key in SCORE_KEYS):
            candidate_scores[question] = {
                key: float(scores[key]) for key in SCORE_KEYS
            }
        deterministic = case.get("deterministic") or {}
        answer = case.get("answer") or ""
        context = render_case_context(
            artifact_cases[question],
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        answer_audit = audit_answer(
            answer, [block["text"] for block in parse_evidence_context(context)]
        )
        completion = completion_rows.get(question, {})
        observed = candidate_scores.get(question, {})
        case_gates[question] = {
            "generation_ok": case.get("generation_status") == "OK",
            "judge_ok": case.get("judge_status") == "OK",
            "score_shape": len(observed) == len(SCORE_KEYS),
            "faithfulness_exact_one": observed.get("faithfulness") == 1.0,
            "answer_relevancy_floor": observed.get("answer_relevancy", -1.0) >= 0.95,
            "context_precision_target": observed.get("context_precision", -1.0) >= 0.90,
            "semantic_drop_bounded": all(
                observed.get(key, -1.0) >= reference[question][key] - 0.10
                for key in ("faithfulness", "answer_relevancy")
            ),
            "citation_correctness": deterministic.get("citation_correctness"),
            "recall_proxy": deterministic.get("recall_proxy"),
            "fallback_correct": deterministic.get("fallback_correct"),
            "answer_integrity_passed": not (
                answer_audit.uncited_answer
                or answer_audit.malformed_line_citations
                or answer_audit.out_of_range_citations
                or answer_audit.unsupported_numeric_claims
                or answer_audit.fallback_answer
            ),
            "unsupported_numeric_claims": list(
                answer_audit.unsupported_numeric_claims
            ),
            "completion_ok": (
                completion.get("applicable") is not True
                or completion.get("final_passed") is True
            ),
            "selector_safe": selector_rows.get(question, {}).get("safe") is True,
            "selector_one_source": selector_rows.get(question, {}).get("source_count") == 1,
            "selector_tier": selector_rows.get(question, {}).get("selector_tier"),
            "reference_scores": reference[question],
            "candidate_scores": observed,
        }

    provider_complete = bool(
        summary.get("provider_complete") is True
        and summary.get("official") is False
        and summary.get("context_strategy") == CONTEXT_STRATEGY_SELECTIVE_V7
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
        and gate["answer_integrity_passed"]
        and not gate["unsupported_numeric_claims"]
        for gate in case_gates.values()
    )
    selector_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        gate["selector_safe"]
        and gate["selector_one_source"]
        and gate["selector_tier"] in SAFE_TIERS
        for gate in case_gates.values()
    )
    semantic_passed = len(case_gates) == len(SENTINEL_QUESTIONS) and all(
        gate["faithfulness_exact_one"]
        and gate["answer_relevancy_floor"]
        and gate["context_precision_target"]
        and gate["semantic_drop_bounded"]
        for gate in case_gates.values()
    )
    candidate_aggregate = (
        _aggregate(candidate_scores)
        if len(candidate_scores) == len(SENTINEL_QUESTIONS)
        else {}
    )
    reference_aggregate = _aggregate(reference)
    generation_bindings = _checkpoint_values(generation_path, "binding")
    judge_bindings = _checkpoint_values(judge_path, "binding")
    judge_contexts = _checkpoint_values(judge_path, "judge_context_fingerprint")
    gates = {
        "provider_complete": provider_complete,
        "single_generation_binding": len(generation_bindings) == 1,
        "complete_checkpoint_provenance": (
            len(_checkpoint_records(generation_path)) == len(SENTINEL_QUESTIONS)
            and len(_checkpoint_records(judge_path)) == len(SENTINEL_QUESTIONS)
            and len(judge_contexts) == 1
        ),
        "selector_contract": selector_passed,
        "deterministic_contracts": deterministic_passed,
        "completion_policy": len(case_gates) == len(SENTINEL_QUESTIONS)
        and all(gate["completion_ok"] for gate in case_gates.values()),
        "bounded_per_case_semantics": semantic_passed,
        "aggregate_faithfulness_exact_one": candidate_aggregate.get(
            "faithfulness", -1.0
        ) == 1.0,
        "aggregate_answer_relevancy_floor": candidate_aggregate.get(
            "answer_relevancy", -1.0
        ) >= 0.95,
        "aggregate_context_precision_target": candidate_aggregate.get(
            "context_precision", -1.0
        ) >= 0.90,
        "aggregate_context_precision_improved": candidate_aggregate.get(
            "context_precision", -1.0
        ) >= reference_aggregate["context_precision"] + 0.15,
        "official_false": summary.get("official") is False,
    }
    return {
        **summary,
        "audit": "priority3_fact_evidence_sufficiency_v2_sentinel",
        "official": False,
        "promotion_eligible": False,
        "replicate_id": replicate_id,
        "selector_fingerprint": FACT_CONTEXT_SELECTOR_FINGERPRINT_V2,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "reference_judge_checkpoint": str(REFERENCE_JUDGE_PATH),
        "reference_judge_checkpoint_sha256": EXPECTED_REFERENCE_JUDGE_SHA256,
        "reference_aggregate": reference_aggregate,
        "candidate_aggregate": candidate_aggregate,
        "selector_rows": selector_rows,
        "case_gates": case_gates,
        "checkpoint_provenance": {
            "generation_checkpoint": str(generation_path),
            "generation_checkpoint_sha256": _sha256(generation_path),
            "judge_checkpoint": str(judge_path),
            "judge_checkpoint_sha256": _sha256(judge_path),
            "generation_binding_values": sorted(generation_bindings),
            "judge_binding_values": sorted(judge_bindings),
            "judge_context_fingerprint_values": sorted(judge_contexts),
        },
        "pre_registered_gates": {
            "nine_fact_cases_complete": True,
            "safe_single_source_for_all_cases": True,
            "faithfulness_exactly_1_0_per_case_and_aggregate": True,
            "answer_relevancy_at_least_0_95_per_case": True,
            "context_precision_at_least_0_90_per_case_and_aggregate": True,
            "context_precision_improvement_at_least_0_15": True,
            "deterministic_integrity_and_provenance": True,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    *,
    replicate_id: str,
    gen_checkpoint: Path | None = None,
    judge_checkpoint: Path | None = None,
    summary_output: Path | None = None,
    report_output: Path | None = None,
    fresh: bool = False,
    max_gen_retries: int = 0,
    max_judge_retries: int = 0,
) -> dict[str, Any]:
    assert_phase2_retrieval_hermeticity()
    default_gen, default_judge, default_summary, default_report = sentinel_artifact_paths(
        replicate_id
    )
    gen_checkpoint = gen_checkpoint or default_gen
    judge_checkpoint = judge_checkpoint or default_judge
    summary_output = summary_output or default_summary
    report_output = report_output or default_report
    if fresh:
        for path in (gen_checkpoint, judge_checkpoint, summary_output, report_output):
            path.unlink(missing_ok=True)

    artifact, upstream = load_bound_artifact(
        ARTIFACT_PATH,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V7,
    )
    selected = sentinel_cases()
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    metadata = {case.question: case for case in selected}
    selector_rows = _selector_rows(artifact)

    def render(case_payload: dict[str, Any]) -> str:
        return render_case_context(
            case_payload,
            required_keywords=metadata[case_payload["question"]].required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
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
        force_non_official=True,
    )
    summary["token_usage_totals"] = tracker.totals
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = build_report(
        summary,
        _reference_scores(),
        selector_rows,
        replicate_id,
        gen_checkpoint,
        judge_checkpoint,
        case_by_question,
    )
    report["summary_path"] = str(summary_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replicate-id", required=True)
    parser.add_argument("--gen-checkpoint", type=Path)
    parser.add_argument("--judge-checkpoint", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    args = parser.parse_args(argv)
    report = run(
        replicate_id=args.replicate_id,
        gen_checkpoint=args.gen_checkpoint,
        judge_checkpoint=args.judge_checkpoint,
        summary_output=args.summary_output,
        report_output=args.report_output,
        fresh=args.fresh,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
