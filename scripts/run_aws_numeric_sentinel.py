"""Run the one-case AWS numeric-pair sentinel over comparative packing v4.

This provider-backed run is deliberately non-official. It spends exactly one
generation call and one judge call unless a provider retry is explicitly
requested. The pre-registered gate requires a grounded, cited, non-fallback
answer that preserves both AWS period/value figures before v4 can advance to a
six-case comparative A/B.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
    run_phase2,
)
from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V4,
    pack_case_context,
    render_packed_blocks,
)
from src.evaluation.generation_checkpoint import (
    GenerationCheckpointStore,
    parse_evidence_context,
    sha256_text,
)
from src.evaluation.judge_checkpoint import JudgeCheckpointStore
from src.evaluation.phase2_runtime import (
    GENERATION_SYSTEM_PROMPT_FINGERPRINT,
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_generation_call,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import Generator


AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
AWS_REQUIRED_VALUES = ("107,556", "128,725")
AWS_REQUIRED_PERIODS = ("2024", "2025")
CONTEXT_REQUIRED_TERMS = (
    *AWS_REQUIRED_VALUES,
    "Microsoft Cloud revenue increased",
    "168.9 billion",
)
MIN_FAITHFULNESS = 0.95
MIN_ANSWER_RELEVANCY = 0.90

OUTPUT_DIR = Path("data/eval_artifacts")
GEN_CHECKPOINT = OUTPUT_DIR / "aws_numeric_v4_gen.jsonl"
JUDGE_CHECKPOINT = OUTPUT_DIR / "aws_numeric_v4_judge.jsonl"
SUMMARY = OUTPUT_DIR / "aws_numeric_v4_summary.json"


def aws_case() -> TestCase:
    """Return the fixed sentinel case with an explicit recall contract."""
    matches = [case for case in TEST_SET if case.question == AWS_QUESTION]
    if len(matches) != 1 or matches[0].category != "comparative":
        raise RuntimeError("AWS sentinel test-case contract drift")
    return replace(matches[0], required_keywords=list(AWS_REQUIRED_VALUES))


def v4_context_renderer(test_case: TestCase) -> Callable[[dict], str]:
    """Build the exact v4 context shared by generation, metrics, and judge."""
    def render(case_payload: dict) -> str:
        packed = pack_case_context(
            case_payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_COMPARATIVE_V4,
        )
        return render_packed_blocks(packed)

    return render


def _score_at_least(scores: dict[str, Any], key: str, minimum: float) -> bool:
    value = scores.get(key)
    return isinstance(value, (int, float)) and float(value) >= minimum


def build_sentinel_report(
    provider_run: dict[str, Any], evidence_context: str
) -> dict[str, Any]:
    """Apply the pre-registered provider, answer, and grounding gates."""
    case = provider_run.get("cases", [{}])[0]
    answer = case.get("answer") or ""
    source_texts = [
        block["text"] for block in parse_evidence_context(evidence_context)
    ]
    audit = audit_answer(answer, source_texts)
    scores = case.get("scores") or {}
    deterministic = case.get("deterministic") or {}
    folded_context = evidence_context.casefold()

    context_contract = {
        term: term.casefold() in folded_context for term in CONTEXT_REQUIRED_TERMS
    }
    answer_values = {term: term in answer for term in AWS_REQUIRED_VALUES}
    answer_periods = {term: term in answer for term in AWS_REQUIRED_PERIODS}
    integrity = {
        "non_fallback": not audit.fallback_answer,
        "exact_values_present": all(answer_values.values()),
        "periods_present": all(answer_periods.values()),
        "canonical_citation_present": bool(audit.canonical_citations),
        "no_legacy_line_citations": audit.malformed_line_citations == 0,
        "no_out_of_range_citations": not audit.out_of_range_citations,
        "not_uncited": not audit.uncited_answer,
        "no_unsupported_numeric_claims": not audit.unsupported_numeric_claims,
    }
    gates = {
        "provider_complete": (
            provider_run.get("provider_complete") is True
            and provider_run.get("num_selected") == 1
            and provider_run.get("num_generation_ok") == 1
            and provider_run.get("num_judged_ok") == 1
            and case.get("generation_status") == "OK"
            and case.get("judge_status") == "OK"
        ),
        "v4_context_contract": all(context_contract.values()),
        "answer_integrity": all(integrity.values()),
        "faithfulness": _score_at_least(
            scores, "faithfulness", MIN_FAITHFULNESS
        ),
        "answer_relevancy": _score_at_least(
            scores, "answer_relevancy", MIN_ANSWER_RELEVANCY
        ),
        "citation_correctness": (
            deterministic.get("citation_correctness") == 1.0
        ),
        "recall_proxy": deterministic.get("recall_proxy") == 1.0,
        "fallback_correctness": deterministic.get("fallback_correct") is True,
    }
    return {
        "schema_version": 1,
        "official": False,
        "reason": "single-case AWS numeric sentinel; not an official benchmark",
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "model": EVAL_MODEL,
        "context_strategy": CONTEXT_STRATEGY_COMPARATIVE_V4,
        "system_prompt_sha256": GENERATION_SYSTEM_PROMPT_FINGERPRINT,
        "evidence_context_sha256": sha256_text(evidence_context),
        "pre_registered_gates": {
            "expected_generation_ok": 1,
            "expected_judgment_ok": 1,
            "required_answer_values": list(AWS_REQUIRED_VALUES),
            "required_answer_periods": list(AWS_REQUIRED_PERIODS),
            "required_context_terms": list(CONTEXT_REQUIRED_TERMS),
            "minimum_faithfulness": MIN_FAITHFULNESS,
            "minimum_answer_relevancy": MIN_ANSWER_RELEVANCY,
            "require_grounded_canonical_citations": True,
            "require_deterministic_metrics": True,
        },
        "context_contract": context_contract,
        "answer_values": answer_values,
        "answer_periods": answer_periods,
        "answer_audit": audit.to_dict(),
        "integrity": integrity,
        "gates": gates,
        "gate_passed": all(gates.values()),
        "provider_run": provider_run,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    args = parser.parse_args(argv)

    if args.fresh:
        for path in (GEN_CHECKPOINT, JUDGE_CHECKPOINT, SUMMARY):
            if path.exists():
                path.unlink()

    artifact, upstream = load_bound_artifact(
        ARTIFACT_PATH,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_COMPARATIVE_V4,
    )
    test_case = aws_case()
    cases = {case["question"]: case for case in artifact["cases"]}
    payload = cases.get(AWS_QUESTION)
    if payload is None:
        raise RuntimeError("AWS sentinel case missing from frozen artifact")
    renderer = v4_context_renderer(test_case)
    evidence_context = renderer(payload)

    tracker = UsageTracker()
    generation = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
    judge = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    provider_run = run_phase2(
        selected=[test_case],
        case_by_question=cases,
        upstream=upstream,
        bound_fingerprint=EXPECTED_ARTIFACT_FINGERPRINT,
        generate_fn=make_generation_call(generation, tracker),
        judge_fn=make_judge_call(judge, tracker),
        generation_store=GenerationCheckpointStore(GEN_CHECKPOINT),
        judge_store=JudgeCheckpointStore(JUDGE_CHECKPOINT),
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
        evidence_context_fn=renderer,
    )
    provider_run["provider_complete"] = bool(provider_run["official"])
    provider_run["official"] = False
    provider_run["reason"] = "single-case sentinel evidence; non-official"
    provider_run["token_usage_totals"] = tracker.totals

    report = build_sentinel_report(provider_run, evidence_context)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
