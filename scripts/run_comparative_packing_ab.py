"""Run the non-official paired provider A/B for comparative packing v3.

Both arms consume the same frozen Phase 1 artifact and the same six priority
<= 2 comparative cases. Checkpoints are strategy-bound and separate. The
pre-registered gate requires complete provider coverage, deterministic-metric
non-regression, a context-precision gain, bounded semantic-score movement, and
an evidence-grounded non-fallback answer for the AWS/Microsoft sentinel.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

import tiktoken

from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    pack_case_context,
    render_packed_blocks,
)
from src.evaluation.generation_checkpoint import (
    GenerationCheckpointStore,
    build_evidence_context,
    parse_evidence_context,
)
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.phase2_runtime import (
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_generation_call,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import Generator


EXPECTED_COMPARATIVE_CASES = 6
MIN_CONTEXT_PRECISION_DELTA = 0.08
MIN_FAITHFULNESS_DELTA = -0.05
MIN_ANSWER_RELEVANCY_DELTA = -0.05
MIN_OVERALL_DELTA = 0.0
MIN_CONTEXT_TOKEN_REDUCTION_PCT = 25.0

AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
AWS_REQUIRED_ANSWER_TERMS = ("107,556", "128,725")

OUTPUT_DIR = Path("data/eval_artifacts")
BASELINE_GEN = OUTPUT_DIR / "comparative_ab_full_gen.jsonl"
BASELINE_JUDGE = OUTPUT_DIR / "comparative_ab_full_judge.jsonl"
CANDIDATE_GEN = OUTPUT_DIR / "comparative_ab_v3_gen.jsonl"
CANDIDATE_JUDGE = OUTPUT_DIR / "comparative_ab_v3_judge.jsonl"
SUMMARY = OUTPUT_DIR / "comparative_packing_v3_ab.json"


def comparative_cases() -> list[TestCase]:
    """Return the fixed priority <= 2 comparative slice."""
    selected = [
        case
        for case in TEST_SET
        if case.priority <= 2 and case.category == "comparative"
    ]
    if len(selected) != EXPECTED_COMPARATIVE_CASES:
        raise RuntimeError(
            "Comparative test-set drift: expected "
            f"{EXPECTED_COMPARATIVE_CASES}, found {len(selected)}"
        )
    return selected


def context_renderer(
    strategy: str,
    metadata: dict[str, TestCase],
) -> Callable[[dict], str]:
    if strategy == CONTEXT_STRATEGY_FULL_EVIDENCE:
        return build_evidence_context
    if strategy != CONTEXT_STRATEGY_COMPARATIVE_V3:
        raise ValueError(f"Unsupported A/B strategy: {strategy}")

    def render(case_payload: dict) -> str:
        packed = pack_case_context(
            case_payload,
            required_keywords=metadata[case_payload["question"]].required_keywords,
            strategy=CONTEXT_STRATEGY_COMPARATIVE_V3,
        )
        return render_packed_blocks(packed)

    return render


def _run_arm(
    *,
    artifact: dict[str, Any],
    strategy: str,
    selected: list[TestCase],
    generation_path: Path,
    judge_path: Path,
    max_gen_retries: int,
    max_judge_retries: int,
) -> dict[str, Any]:
    _, upstream = load_bound_artifact(
        ARTIFACT_PATH,
        EXPECTED_ARTIFACT_FINGERPRINT,
        strategy,
    )
    metadata = {case.question: case for case in selected}
    renderer = context_renderer(strategy, metadata)
    case_by_question = {
        case["question"]: case for case in artifact["cases"]
    }
    tracker = UsageTracker()
    generation = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
    judge = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    result = run_phase2(
        selected=selected,
        case_by_question=case_by_question,
        upstream=upstream,
        bound_fingerprint=EXPECTED_ARTIFACT_FINGERPRINT,
        generate_fn=make_generation_call(generation, tracker),
        judge_fn=make_judge_call(judge, tracker),
        generation_store=GenerationCheckpointStore(generation_path),
        judge_store=JudgeCheckpointStore(judge_path),
        max_gen_retries=max_gen_retries,
        max_judge_retries=max_judge_retries,
        evidence_context_fn=renderer,
    )
    result["provider_complete"] = bool(result["official"])
    result["official"] = False
    result["reason"] = "comparative subset arm; non-official A/B evidence"
    result["token_usage_totals"] = tracker.totals
    return result


def _metric_delta(
    baseline: dict[str, Any], candidate: dict[str, Any], key: str
) -> float | None:
    before = baseline.get("metrics", {}).get(key)
    after = candidate.get("metrics", {}).get(key)
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return None
    return round(float(after) - float(before), 4)


def _deterministic_non_regression(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, bool]:
    keys = (
        "citation_correctness_avg",
        "recall_proxy_avg",
        "fallback_accuracy",
    )
    checks: dict[str, bool] = {}
    for key in keys:
        before = baseline.get("deterministic", {}).get(key)
        after = candidate.get("deterministic", {}).get(key)
        checks[key] = (
            isinstance(before, (int, float))
            and isinstance(after, (int, float))
            and float(after) >= float(before)
        )
    return checks


def _contexts_and_tokens(
    artifact: dict[str, Any], selected: list[TestCase]
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    cases = {case["question"]: case for case in artifact["cases"]}
    metadata = {case.question: case for case in selected}
    full_renderer = context_renderer(CONTEXT_STRATEGY_FULL_EVIDENCE, metadata)
    v3_renderer = context_renderer(CONTEXT_STRATEGY_COMPARATIVE_V3, metadata)
    encoder = tiktoken.get_encoding("cl100k_base")
    contexts: dict[str, dict[str, str]] = {}
    full_tokens = 0
    v3_tokens = 0
    for case in selected:
        payload = cases[case.question]
        full = full_renderer(payload)
        v3 = v3_renderer(payload)
        contexts[case.question] = {
            CONTEXT_STRATEGY_FULL_EVIDENCE: full,
            CONTEXT_STRATEGY_COMPARATIVE_V3: v3,
        }
        full_tokens += len(encoder.encode(full))
        v3_tokens += len(encoder.encode(v3))
    reduction = round(
        100.0 * (full_tokens - v3_tokens) / max(full_tokens, 1), 2
    )
    return contexts, {
        "baseline_tokens": full_tokens,
        "candidate_tokens": v3_tokens,
        "reduction_pct": reduction,
    }


def build_paired_report(
    *,
    artifact: dict[str, Any],
    selected: list[TestCase],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    contexts, context_tokens = _contexts_and_tokens(artifact, selected)
    baseline_cases = {case["question"]: case for case in baseline["cases"]}
    candidate_cases = {case["question"]: case for case in candidate["cases"]}
    paired_cases: list[dict[str, Any]] = []
    for test_case in selected:
        question = test_case.question
        before = baseline_cases[question]
        after = candidate_cases[question]
        full_sources = [
            block["text"]
            for block in parse_evidence_context(
                contexts[question][CONTEXT_STRATEGY_FULL_EVIDENCE]
            )
        ]
        v3_sources = [
            block["text"]
            for block in parse_evidence_context(
                contexts[question][CONTEXT_STRATEGY_COMPARATIVE_V3]
            )
        ]
        before_audit = audit_answer(before.get("answer") or "", full_sources)
        after_audit = audit_answer(after.get("answer") or "", v3_sources)
        score_deltas = {
            key: (
                round(float(after["scores"][key]) - float(before["scores"][key]), 4)
                if before.get("scores") and after.get("scores")
                else None
            )
            for key in ("faithfulness", "answer_relevancy", "context_precision")
        }
        paired_cases.append(
            {
                "question": question,
                "baseline_scores": before.get("scores"),
                "candidate_scores": after.get("scores"),
                "score_deltas": score_deltas,
                "baseline_fallback": before_audit.fallback_answer,
                "candidate_fallback": after_audit.fallback_answer,
                "candidate_audit": after_audit.to_dict(),
            }
        )

    aws = next(row for row in paired_cases if row["question"] == AWS_QUESTION)
    aws_answer = candidate_cases[AWS_QUESTION].get("answer") or ""
    aws_gate = {
        "non_fallback": not aws["candidate_fallback"],
        "required_terms_present": all(
            term in aws_answer for term in AWS_REQUIRED_ANSWER_TERMS
        ),
        "canonical_citation_present": bool(
            aws["candidate_audit"]["canonical_citations"]
        ),
        "no_out_of_range_citations": not aws["candidate_audit"][
            "out_of_range_citations"
        ],
        "no_unsupported_numeric_claims": not aws["candidate_audit"][
            "unsupported_numeric_claims"
        ],
    }
    deltas = {
        key: _metric_delta(baseline, candidate, key)
        for key in (
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "overall_judge_average",
        )
    }
    deterministic = _deterministic_non_regression(baseline, candidate)
    gates = {
        "provider_complete": (
            baseline.get("provider_complete") is True
            and candidate.get("provider_complete") is True
            and baseline.get("num_selected") == EXPECTED_COMPARATIVE_CASES
            and candidate.get("num_selected") == EXPECTED_COMPARATIVE_CASES
        ),
        "context_token_reduction": (
            context_tokens["reduction_pct"]
            >= MIN_CONTEXT_TOKEN_REDUCTION_PCT
        ),
        "context_precision": (
            deltas["context_precision"] is not None
            and deltas["context_precision"] >= MIN_CONTEXT_PRECISION_DELTA
        ),
        "faithfulness": (
            deltas["faithfulness"] is not None
            and deltas["faithfulness"] >= MIN_FAITHFULNESS_DELTA
        ),
        "answer_relevancy": (
            deltas["answer_relevancy"] is not None
            and deltas["answer_relevancy"] >= MIN_ANSWER_RELEVANCY_DELTA
        ),
        "overall": (
            deltas["overall_judge_average"] is not None
            and deltas["overall_judge_average"] >= MIN_OVERALL_DELTA
        ),
        "deterministic_non_regression": all(deterministic.values()),
        "aws_answer_integrity": all(aws_gate.values()),
    }
    return {
        "schema_version": 1,
        "official": False,
        "reason": "paired comparative subset; not an official benchmark",
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "model": EVAL_MODEL,
        "pre_registered_gates": {
            "expected_cases_per_arm": EXPECTED_COMPARATIVE_CASES,
            "minimum_context_precision_delta": MIN_CONTEXT_PRECISION_DELTA,
            "minimum_faithfulness_delta": MIN_FAITHFULNESS_DELTA,
            "minimum_answer_relevancy_delta": MIN_ANSWER_RELEVANCY_DELTA,
            "minimum_overall_delta": MIN_OVERALL_DELTA,
            "minimum_context_token_reduction_pct": (
                MIN_CONTEXT_TOKEN_REDUCTION_PCT
            ),
            "aws_required_answer_terms": list(AWS_REQUIRED_ANSWER_TERMS),
        },
        "baseline": baseline,
        "candidate": candidate,
        "context_tokens": context_tokens,
        "metric_deltas": deltas,
        "deterministic_non_regression": deterministic,
        "aws_gate": aws_gate,
        "gates": gates,
        "gate_passed": all(gates.values()),
        "paired_cases": paired_cases,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    args = parser.parse_args(argv)

    paths = (
        BASELINE_GEN,
        BASELINE_JUDGE,
        CANDIDATE_GEN,
        CANDIDATE_JUDGE,
        SUMMARY,
    )
    if args.fresh:
        for path in paths:
            if path.exists():
                path.unlink()

    artifact, _ = load_bound_artifact(
        ARTIFACT_PATH,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_FULL_EVIDENCE,
    )
    selected = comparative_cases()
    baseline = _run_arm(
        artifact=artifact,
        strategy=CONTEXT_STRATEGY_FULL_EVIDENCE,
        selected=selected,
        generation_path=BASELINE_GEN,
        judge_path=BASELINE_JUDGE,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
    )
    if not baseline["provider_complete"]:
        partial = {
            "official": False,
            "reason": "baseline arm incomplete; rerun to resume",
            "baseline": baseline,
            "gate_passed": False,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(
            json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(partial, ensure_ascii=False, indent=2))
        return 1

    candidate = _run_arm(
        artifact=artifact,
        strategy=CONTEXT_STRATEGY_COMPARATIVE_V3,
        selected=selected,
        generation_path=CANDIDATE_GEN,
        judge_path=CANDIDATE_JUDGE,
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
    )
    report = build_paired_report(
        artifact=artifact,
        selected=selected,
        baseline=baseline,
        candidate=candidate,
    )
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
