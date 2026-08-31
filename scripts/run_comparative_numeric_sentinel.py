"""Run a focused numeric-contract sentinel over selective packing v2.

This provider-backed run is deliberately non-official. It exercises the two
comparative cases that currently carry the strongest numeric-grounding risk:
Apple/Microsoft services revenue and AWS/Microsoft cloud growth. Both cases
must receive complete, cited answers from the exact v2-rendered contexts;
derived values that are not printed in the evidence are rejected by the
deterministic answer audit.
"""

from __future__ import annotations

import argparse
import json
import logging
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
    CONTEXT_STRATEGY_SELECTIVE_V2,
    render_case_context,
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
    make_period_value_postprocessor,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import Generator

logger = logging.getLogger(__name__)


APPLE_QUESTION = "Compare Apple and Microsoft's approach to cloud/services revenue."
AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)
AWS_REQUIRED_VALUES = ("107,556", "128,725")
AWS_REQUIRED_PERIODS = ("2024", "2025")
APPLE_CONTEXT_TERMS = ("Services", "Azure")
# This semantic regression was not a retrieval miss: the answer compared
# reporting formats instead of the revenue approach asked about. Sentinel-only
# lexical gates pin the requested dimension without feeding answer labels into
# production selection or generation.
APPLE_APPROACH_ALTERNATIVES = (
    "cloud services",
    "cloud storage",
    "App Store",
    "advertising",
)
MICROSOFT_APPROACH_TERM = "Azure"
AWS_CONTEXT_TERMS = (
    *AWS_REQUIRED_VALUES,
    "Microsoft Cloud revenue increased",
    "168.9 billion",
)
# These were observed in the previous comparative A/B answer even though
# neither value was printed in the rendered Apple/Microsoft evidence.
APPLE_FORBIDDEN_DERIVED_TERMS = ("12,989", "13.5%")

MIN_FAITHFULNESS = 0.90
MIN_ANSWER_RELEVANCY = 0.90
OUTPUT_DIR = Path("data/eval_artifacts")
GEN_CHECKPOINT = OUTPUT_DIR / "comparative_numeric_v2_gen.jsonl"
JUDGE_CHECKPOINT = OUTPUT_DIR / "comparative_numeric_v2_judge.jsonl"
SUMMARY = OUTPUT_DIR / "comparative_numeric_v2_summary.json"


def sentinel_cases() -> list[TestCase]:
    """Return the fixed two-case slice with explicit AWS value recall."""
    by_question = {case.question: case for case in TEST_SET}
    missing = [
        question for question in (APPLE_QUESTION, AWS_QUESTION)
        if question not in by_question
    ]
    if missing or any(by_question[q].category != "comparative" for q in by_question if q in (APPLE_QUESTION, AWS_QUESTION)):
        raise RuntimeError("comparative numeric sentinel test-case contract drift")
    return [
        by_question[APPLE_QUESTION],
        replace(by_question[AWS_QUESTION], required_keywords=list(AWS_REQUIRED_VALUES)),
    ]


def context_renderer(
    selected: list[TestCase],
) -> Callable[[dict[str, Any]], str]:
    """Build the exact v2 context shared by generation, metrics, and judge."""
    metadata = {case.question: case for case in selected}

    def render(case_payload: dict[str, Any]) -> str:
        question = case_payload.get("question")
        test_case = metadata.get(question)
        if test_case is None:
            raise RuntimeError(f"sentinel renderer received unknown case: {question!r}")
        return render_case_context(
            case_payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V2,
        )

    return render


def _score_at_least(scores: dict[str, Any], key: str, minimum: float) -> bool:
    value = scores.get(key)
    return isinstance(value, (int, float)) and float(value) >= minimum


def _case_report(
    case: dict[str, Any],
    evidence_context: str,
) -> dict[str, Any]:
    """Apply deterministic contracts and semantic score gates to one case."""
    answer = case.get("answer") or ""
    source_texts = [
        block["text"] for block in parse_evidence_context(evidence_context)
    ]
    audit = audit_answer(answer, source_texts)
    scores = case.get("scores") or {}
    deterministic = case.get("deterministic") or {}
    question = case.get("question")
    is_aws = question == AWS_QUESTION
    required_values = AWS_REQUIRED_VALUES if is_aws else ()
    required_periods = AWS_REQUIRED_PERIODS if is_aws else ()
    context_terms = AWS_CONTEXT_TERMS if is_aws else APPLE_CONTEXT_TERMS
    folded_context = evidence_context.casefold()

    context_contract = {
        term: term.casefold() in folded_context for term in context_terms
    }
    answer_values = {term: term in answer for term in required_values}
    answer_periods = {term: term in answer for term in required_periods}
    forbidden_derived = {
        term: term.casefold() in answer.casefold()
        for term in APPLE_FORBIDDEN_DERIVED_TERMS
    } if not is_aws else {}
    folded_answer = answer.casefold()
    approach_terms = {} if is_aws else {
        "apple_revenue_approach": any(
            term.casefold() in folded_answer
            for term in APPLE_APPROACH_ALTERNATIVES
        ),
        "microsoft_revenue_approach": (
            MICROSOFT_APPROACH_TERM.casefold() in folded_answer
        ),
    }
    integrity = {
        "non_fallback": not audit.fallback_answer,
        "exact_values_present": all(answer_values.values()),
        "periods_present": all(answer_periods.values()),
        "canonical_citation_present": bool(audit.canonical_citations),
        "no_legacy_line_citations": audit.malformed_line_citations == 0,
        "no_out_of_range_citations": not audit.out_of_range_citations,
        "not_uncited": not audit.uncited_answer,
        "no_unsupported_numeric_claims": not audit.unsupported_numeric_claims,
        "no_forbidden_derived_terms": not any(forbidden_derived.values()),
        "requested_approach_answered": all(approach_terms.values()),
    }
    gates = {
        "generation_ok": case.get("generation_status") == "OK",
        "judge_ok": case.get("judge_status") == "OK",
        "context_contract": all(context_contract.values()),
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
        "question": question,
        "answer": answer,
        "context_sha256": sha256_text(evidence_context),
        "context_terms": context_contract,
        "answer_values": answer_values,
        "answer_periods": answer_periods,
        "forbidden_derived_terms": forbidden_derived,
        "approach_terms": approach_terms,
        "answer_audit": audit.to_dict(),
        "integrity": integrity,
        "scores": scores,
        "deterministic": deterministic,
        "gates": gates,
        "gate_passed": all(gates.values()),
    }


def build_sentinel_report(
    provider_run: dict[str, Any],
    evidence_contexts: dict[str, str],
) -> dict[str, Any]:
    """Build the non-official report from one shared provider run."""
    case_reports = [
        _case_report(case, evidence_contexts[case["question"]])
        for case in provider_run.get("cases", [])
        if case.get("question") in evidence_contexts
    ]
    expected_questions = {APPLE_QUESTION, AWS_QUESTION}
    observed_questions = {report["question"] for report in case_reports}
    provider_complete = (
        provider_run.get("provider_complete") is True
        and provider_run.get("num_selected") == len(expected_questions)
        and provider_run.get("num_generation_ok") == len(expected_questions)
        and provider_run.get("num_judged_ok") == len(expected_questions)
        and observed_questions == expected_questions
        and all(report["gates"]["generation_ok"] for report in case_reports)
        and all(report["gates"]["judge_ok"] for report in case_reports)
    )
    context_contract = {
        report["question"]: report["context_terms"] for report in case_reports
    }
    answer_integrity = {
        report["question"]: report["integrity"] for report in case_reports
    }
    numeric_contract = {
        "apple_no_derived_values": (
            bool(case_reports)
            and next(
                (r for r in case_reports if r["question"] == APPLE_QUESTION),
                {"forbidden_derived_terms": {}},
            )["forbidden_derived_terms"] == {
                term: False for term in APPLE_FORBIDDEN_DERIVED_TERMS
            }
        ),
        "aws_exact_values_and_periods": (
            bool(case_reports)
            and next(
                (r for r in case_reports if r["question"] == AWS_QUESTION),
                {"answer_values": {}, "answer_periods": {}},
            )["answer_values"] == {
                term: True for term in AWS_REQUIRED_VALUES
            }
            and next(
                (r for r in case_reports if r["question"] == AWS_QUESTION),
                {"answer_values": {}, "answer_periods": {}},
            )["answer_periods"] == {
                term: True for term in AWS_REQUIRED_PERIODS
            }
        ),
    }
    apple_case = next(
        (r for r in case_reports if r["question"] == APPLE_QUESTION),
        {"approach_terms": {}},
    )
    approach_contract = {
        "apple_revenue_approach": (
            apple_case["approach_terms"].get("apple_revenue_approach") is True
        ),
        "microsoft_revenue_approach": (
            apple_case["approach_terms"].get("microsoft_revenue_approach") is True
        ),
    }
    correction_rows = provider_run.get("period_value_corrections") or {}
    apple_correction = correction_rows.get(APPLE_QUESTION, {})
    aws_correction = correction_rows.get(AWS_QUESTION, {})
    correction_contract = {
        "apple_not_applicable_without_correction": (
            apple_correction.get("applicable") is False
            and apple_correction.get("correction_attempted") is False
            and apple_correction.get("final_passed") is True
        ),
        "aws_applicable_and_final_complete": (
            aws_correction.get("applicable") is True
            and aws_correction.get("final_passed") is True
            and (
                aws_correction.get("correction_attempted") is False
                or aws_correction.get("correction_accepted") is True
            )
        ),
    }
    gates = {
        "provider_complete": provider_complete,
        "context_contract": (
            len(case_reports) == len(expected_questions)
            and all(
                all(values.values()) for values in context_contract.values()
            )
        ),
        "answer_integrity": (
            len(case_reports) == len(expected_questions)
            and all(all(values.values()) for values in answer_integrity.values())
        ),
        "numeric_contract": all(numeric_contract.values()),
        "approach_contract": all(approach_contract.values()),
        "bounded_correction": all(correction_contract.values()),
        "semantic_scores": (
            len(case_reports) == len(expected_questions)
            and all(
                report["gates"]["faithfulness"]
                and report["gates"]["answer_relevancy"]
                for report in case_reports
            )
        ),
        "deterministic_metrics": (
            len(case_reports) == len(expected_questions)
            and all(
                report["gates"][key]
                for report in case_reports
                for key in (
                    "citation_correctness",
                    "recall_proxy",
                    "fallback_correctness",
                )
            )
        ),
        "candidate_strategy": (
            provider_run.get("context_strategy") == CONTEXT_STRATEGY_SELECTIVE_V2
        ),
    }
    return {
        "schema_version": 1,
        "official": False,
        "reason": (
            "two-case comparative numeric sentinel under selective v2; "
            "not an official benchmark"
        ),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "model": EVAL_MODEL,
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "system_prompt_sha256": GENERATION_SYSTEM_PROMPT_FINGERPRINT,
        "pre_registered_gates": {
            "expected_cases": [APPLE_QUESTION, AWS_QUESTION],
            "required_apple_context_terms": list(APPLE_CONTEXT_TERMS),
            "required_aws_context_terms": list(AWS_CONTEXT_TERMS),
            "required_aws_answer_values": list(AWS_REQUIRED_VALUES),
            "required_aws_answer_periods": list(AWS_REQUIRED_PERIODS),
            "forbidden_apple_derived_terms": list(APPLE_FORBIDDEN_DERIVED_TERMS),
            "required_apple_approach_alternatives": list(
                APPLE_APPROACH_ALTERNATIVES
            ),
            "required_microsoft_approach_term": MICROSOFT_APPROACH_TERM,
            "minimum_faithfulness": MIN_FAITHFULNESS,
            "minimum_answer_relevancy": MIN_ANSWER_RELEVANCY,
            "require_grounded_canonical_citations": True,
            "require_deterministic_metrics": True,
            "maximum_corrections_per_case": 1,
        },
        "cases": case_reports,
        "context_contract": context_contract,
        "answer_integrity": answer_integrity,
        "numeric_contract": numeric_contract,
        "approach_contract": approach_contract,
        "correction_contract": correction_contract,
        "gates": gates,
        "gate_passed": all(gates.values()),
        "token_usage_totals": provider_run.get("token_usage_totals", {}),
        "provider_run": provider_run,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--max-gen-retries", type=int, default=0)
    parser.add_argument("--max-judge-retries", type=int, default=0)
    parser.add_argument("--gen-checkpoint", type=Path, default=GEN_CHECKPOINT)
    parser.add_argument("--judge-checkpoint", type=Path, default=JUDGE_CHECKPOINT)
    parser.add_argument("--output", type=Path, default=SUMMARY)
    args = parser.parse_args(argv)

    if args.fresh:
        for path in (args.gen_checkpoint, args.judge_checkpoint, args.output):
            if path.exists():
                path.unlink()

    artifact, upstream = load_bound_artifact(
        ARTIFACT_PATH,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V2,
    )
    selected = sentinel_cases()
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    missing = [case.question for case in selected if case.question not in case_by_question]
    if missing:
        raise RuntimeError(f"sentinel cases missing from frozen artifact: {missing}")
    renderer = context_renderer(selected)
    evidence_contexts = {
        case.question: renderer(case_by_question[case.question])
        for case in selected
    }

    tracker = UsageTracker()
    generation = Generator(model=EVAL_MODEL, api_keys=generation_pool_keys())
    judge = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    raw_generate = make_generation_call(generation, tracker)
    correction_rows: dict[str, dict[str, Any]] = {}
    previous_token_usage: dict[str, int] = {}
    if args.output.exists():
        try:
            previous = json.loads(args.output.read_text(encoding="utf-8"))
            previous_run = previous.get("provider_run") or {}
            if previous_run.get("binding") == upstream.binding:
                correction_rows.update(
                    previous_run.get("period_value_corrections") or {}
                )
                previous_token_usage.update(
                    previous_run.get("token_usage_totals") or {}
                )
        except (OSError, json.JSONDecodeError):
            logger.warning("Ignoring unreadable prior sentinel summary: %s", args.output)

    provider_run = run_phase2(
        selected=selected,
        case_by_question=case_by_question,
        upstream=upstream,
        bound_fingerprint=EXPECTED_ARTIFACT_FINGERPRINT,
        generate_fn=raw_generate,
        judge_fn=make_judge_call(judge, tracker),
        generation_store=GenerationCheckpointStore(args.gen_checkpoint),
        judge_store=JudgeCheckpointStore(args.judge_checkpoint),
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
        evidence_context_fn=renderer,
        answer_postprocessor=make_period_value_postprocessor(
            raw_generate, correction_rows
        ),
        answer_completion_metadata=correction_rows,
    )
    provider_run["provider_complete"] = bool(provider_run["official"])
    provider_run["official"] = False
    provider_run["reason"] = "two-case sentinel evidence; non-official"
    provider_run["token_usage_totals"] = {
        key: previous_token_usage.get(key, 0) + value
        for key, value in tracker.totals.items()
    }
    provider_run["period_value_corrections"] = correction_rows

    report = build_sentinel_report(provider_run, evidence_contexts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
