"""Quota probe: exercise Phase 2A/2B on a tiny subset only.

NOT a benchmark. This runner verifies the two-phase plumbing end to end
(parsing, checkpointing, binding, quota stop behavior) on a tiny subset
with explicit guardrails:

- model openai/gpt-oss-120b for BOTH generation and judging (self-judge
  bias is expected and results are never official)
- the same ``selective_packed_v2`` renderer and generation binding used by
  the default official Phase 2 runner
- strictly sequential cases, one draft generation plus at most one bounded
  period/value correction generation, then one judge call each (judge allows
  at most one retry; draft generation none)
- separate generation/judge checkpoint files bound to the Phase 1
  artifact hash; retrieval is never rerun
- any quota error stops the whole probe immediately after checkpointing

Usage:
    python -m scripts.run_quota_probe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.evaluator import (
    JUDGE_PROMPT_TEMPLATE,
    compute_citation_correctness,
)
from src.evaluation.generation_checkpoint import (
    GEN_STATUS_OK,
    GEN_STATUS_SKIPPED_QUOTA,
    GenerationCheckpointStore,
    GenerationUpstream,
    parse_evidence_context,
    run_generation_phase,
    sha256_text,
)
from src.evaluation.test_set import TEST_SET
from src.evaluation.judge_checkpoint import (
    JUDGE_STATUS_OK,
    JUDGE_STATUS_PARSE_INVALID,
    JUDGE_STATUS_SKIPPED_QUOTA,
    JudgeCheckpointStore,
    build_official_aggregate,
    load_judge_records,
    run_judge_phase,
)
from src.evaluation.phase2_runtime import (
    GENERATION_SYSTEM_PROMPT_FINGERPRINT,
    PHASE2_MAX_TOKENS,
    JUDGE_CONTEXT_BUILDER_FINGERPRINT,
    UsageTracker,
    build_production_judge_prompt,
    generation_pool_keys,
    judging_pool_keys,
    make_generation_call,
    make_judge_call,
    make_answer_completion_postprocessor,
)
from src.generation.generator import Generator
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ARTIFACT_PATH = Path(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json"
)
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:f6d2cada527b6ded976570b2065ae6150d5868aaee4ecfc3201d7d46d0a41460"
)
GEN_CHECKPOINT_PATH = Path("data/eval_artifacts/probe_gen.jsonl")
JUDGE_CHECKPOINT_PATH = Path("data/eval_artifacts/probe_judge.jsonl")
SUMMARY_PATH = Path("data/eval_artifacts/probe_summary.json")

PROBE_MODEL = "openai/gpt-oss-120b"
PROBE_CONTEXT_STRATEGY = CONTEXT_STRATEGY_SELECTIVE_V2
DEFAULT_PROBE_QUESTIONS = [
    "What was Apple's total net sales in fiscal year 2024?",
    "Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?",
    "How did Microsoft's total assets change year over year?",
]
PROBE_QUESTIONS = DEFAULT_PROBE_QUESTIONS + [
    "Which company depends more on cloud/subscription revenue, Microsoft or Apple?",
]
GROUND_TRUTHS = {
    PROBE_QUESTIONS[0]: (
        "Apple's total net sales in fiscal year 2024 were $391,035 million."
    ),
    PROBE_QUESTIONS[1]: (
        "In fiscal year 2024, Amazon's consolidated net sales ($637,959 "
        "million) were significantly higher than Apple's total net sales "
        "($391,035 million)."
    ),
    PROBE_QUESTIONS[2]: (
        "Microsoft's total assets grew from $512,163M to $619,003M."
    ),
    PROBE_QUESTIONS[3]: (
        "Microsoft depends more on cloud revenue as a core business driver than "
        "Apple depends on Services."
    ),
}

COMPARATIVE_ACCEPTANCE_VALUES = ("391,035", "637,959")
ANSWERABILITY_ACCEPTANCE_QUESTION = PROBE_QUESTIONS[3]


def build_probe_acceptance(
    question: str,
    answer: str,
    citation_correctness: float | None,
) -> dict | None:
    """Deterministic acceptance checks for the comparative re-probe.

    The evaluation contract pins fiscal year 2024 inside the question
    itself, so the acceptance values and the question now agree by
    construction; a latest-year answer is a contract violation instead of
    an ambiguous judgment call.
    """
    if question == ANSWERABILITY_ACCEPTANCE_QUESTION:
        lowered = answer.casefold()
        return {
            "non_fallback": "could not find sufficient information" not in lowered,
            "mentions_cloud": "cloud" in lowered,
            "mentions_services": "services" in lowered,
            "citation_correctness_pass": citation_correctness == 1.0,
            "passed": (
                "could not find sufficient information" not in lowered
                and "cloud" in lowered
                and "services" in lowered
                and citation_correctness == 1.0
            ),
        }
    if question != PROBE_QUESTIONS[1]:
        return None
    compact = "".join(answer.split())
    lowered = answer.casefold()
    values = {
        value: value in compact
        for value in COMPARATIVE_ACCEPTANCE_VALUES
    }
    identifies_amazon_higher = "amazon" in lowered and "higher" in lowered
    citations_pass = citation_correctness == 1.0
    return {
        "expected_fy2024_values": values,
        "identifies_amazon_higher": identifies_amazon_higher,
        "citation_correctness_pass": citations_pass,
        "passed": all(values.values()) and identifies_amazon_higher and citations_pass,
    }


class ProbeQuotaStop(Exception):
    """Raised to unwind the sequential probe after a quota checkpoint."""


def build_probe_contexts(
    case_by_question: dict[str, dict],
    selected_questions: list[str],
    strategy: str = PROBE_CONTEXT_STRATEGY,
) -> dict[str, str]:
    """Render the exact default official context for each probe case."""
    metadata = {case.question: case for case in TEST_SET}
    missing_metadata = [q for q in selected_questions if q not in metadata]
    if missing_metadata:
        raise RuntimeError(
            f"Probe questions absent from TEST_SET: {missing_metadata}"
        )
    return {
        question: render_case_context(
            case_by_question[question],
            required_keywords=metadata[question].required_keywords,
            strategy=strategy,
        )
        for question in selected_questions
    }


def audit_probe_answer(answer: str, evidence_context: str) -> dict:
    """Apply deterministic integrity gates against the exact probe context."""
    source_blocks = parse_evidence_context(evidence_context)
    source_texts = [block["text"] for block in source_blocks]
    answer_audit = audit_answer(answer, source_texts)
    citation_correctness = compute_citation_correctness(
        answer,
        len(source_blocks),
    )
    integrity = {
        "non_fallback": not answer_audit.fallback_answer,
        "canonical_citation_present": bool(answer_audit.canonical_citations),
        "not_uncited": not answer_audit.uncited_answer,
        "no_legacy_line_citations": (
            answer_audit.malformed_line_citations == 0
        ),
        "no_out_of_range_citations": not answer_audit.out_of_range_citations,
        "no_unsupported_numeric_claims": (
            not answer_audit.unsupported_numeric_claims
        ),
    }
    return {
        "num_sources": len(source_blocks),
        "citation_correctness": citation_correctness,
        "answer_audit": answer_audit.to_dict(),
        "integrity": integrity,
        "integrity_passed": all(integrity.values()),
    }


def _load_artifact_and_binding(
    artifact_path: Path,
    expected_fingerprint: str,
    context_strategy: str,
) -> tuple[dict, GenerationUpstream]:
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 1 artifact missing: {artifact_path}. Run "
            "scripts.run_evaluation_phase1 first."
        )
    raw_bytes = artifact_path.read_bytes()
    artifact = json.loads(raw_bytes.decode("utf-8"))
    if artifact["fingerprints"].get("query_shaper") != QUERY_SHAPER_FINGERPRINT:
        raise RuntimeError(
            "Query-shaper provenance drift: rebuild Phase 1 before running "
            "the probe."
        )
    if artifact["fingerprints"].get("lexical_ladder") != LEXICAL_LADDER_FINGERPRINT:
        raise RuntimeError(
            "Lexical-ladder provenance drift: rebuild Phase 1 before running "
            "the probe."
        )
    embedded = artifact["fingerprints"]["artifact"]
    if embedded != expected_fingerprint:
        raise RuntimeError(
            f"Artifact fingerprint drift: expected {expected_fingerprint}, "
            f"found {embedded}. Refusing to bind the probe to unknown evidence."
        )
    file_sha = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    upstream = GenerationUpstream(
        artifact_path=artifact_path,
        artifact_sha256=file_sha,
        artifact_schema_version=artifact["schema_version"],
        model=PROBE_MODEL,
        system_prompt_sha256=GENERATION_SYSTEM_PROMPT_FINGERPRINT,
        context_strategy=context_strategy,
    )
    return artifact, upstream


def _generation_pool_keys() -> list[str]:
    return generation_pool_keys()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete existing probe checkpoints before running.",
    )
    parser.add_argument(
        "--question",
        action="append",
        choices=PROBE_QUESTIONS,
        help=(
            "Probe only this question; repeat for multiple questions. "
            "Defaults to the original three-case probe."
        ),
    )
    parser.add_argument(
        "--gen-checkpoint",
        type=Path,
        default=GEN_CHECKPOINT_PATH,
        help="Override the generation checkpoint path for this probe run.",
    )
    parser.add_argument(
        "--judge-checkpoint",
        type=Path,
        default=JUDGE_CHECKPOINT_PATH,
        help="Override the judge checkpoint path for this probe run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SUMMARY_PATH,
        help="Override the probe summary output path.",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ARTIFACT_PATH,
        help="Phase 1 artifact to probe.",
    )
    parser.add_argument(
        "--expected-fingerprint",
        default=EXPECTED_ARTIFACT_FINGERPRINT,
        help="Embedded Phase 1 artifact fingerprint.",
    )
    parser.add_argument(
        "--context-strategy",
        choices=[CONTEXT_STRATEGY_SELECTIVE_V2, CONTEXT_STRATEGY_SELECTIVE_V7],
        default=PROBE_CONTEXT_STRATEGY,
        help="Context strategy used for the probe binding.",
    )
    args = parser.parse_args(argv)
    selected_questions = args.question or DEFAULT_PROBE_QUESTIONS

    for path in (args.gen_checkpoint, args.judge_checkpoint):
        if args.fresh and path.exists():
            path.unlink()
            logger.info("Deleted stale probe checkpoint: %s", path)

    artifact, upstream = _load_artifact_and_binding(
        args.artifact,
        args.expected_fingerprint,
        args.context_strategy,
    )
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    missing = [q for q in selected_questions if q not in case_by_question]
    if missing:
        raise RuntimeError(f"Probe questions absent from artifact: {missing}")
    evidence_contexts = build_probe_contexts(
        case_by_question, selected_questions, args.context_strategy
    )

    def probe_context(case_payload: dict) -> str:
        return evidence_contexts[case_payload["question"]]

    # Hermeticity by construction instead of a socket guard: no retrieval
    # EXECUTION happens here. The generator's type-only import chain
    # (retriever.RetrievedChunk -> embedder -> vector_store) is allowed;
    # any heavier retrieval machinery (hybrid, chunk loader, manifests)
    # would indicate retrieval work sneaking back into Phase 2.
    _allowed_retrieval_modules = {
        "src.retrieval",
        "src.retrieval.retriever",
        "src.retrieval.embedder",
        "src.retrieval.vector_store",
        # Phase 2 imports these only to validate the frozen artifact's
        # provenance; they do not execute retrieval.
        "src.retrieval.lexical_ladder",
        "src.retrieval.query_shaper",
    }
    forbidden = [
        name for name in sys.modules
        if name.startswith("src.retrieval")
        and name not in _allowed_retrieval_modules
    ]
    if forbidden:
        raise RuntimeError(f"Retrieval machinery loaded in probe: {forbidden}")

    generation_generator = Generator(
        model=PROBE_MODEL, api_keys=_generation_pool_keys()
    )
    judge_generator = Generator(model=PROBE_MODEL, api_keys=judging_pool_keys())
    generation_store = GenerationCheckpointStore(args.gen_checkpoint)
    judge_store = JudgeCheckpointStore(args.judge_checkpoint)
    tracker = UsageTracker()
    generation_call = make_generation_call(
        generation_generator, tracker
    )
    correction_rows: dict[str, dict] = {}
    answer_postprocessor = make_answer_completion_postprocessor(
        generation_call, correction_rows
    )

    per_case: list[dict] = []
    stopped_reason = None
    for question in selected_questions:
        logger.info("=== PROBE CASE: %s", question[:70])

        gen_records = run_generation_phase(
            selected_questions=[question],
            artifact_cases=case_by_question,
            upstream=upstream,
            generate_fn=generation_call,
            checkpoint_store=generation_store,
            max_retries=0,
            sleep_fn=lambda seconds: None,
            evidence_context_fn=probe_context,
            answer_postprocessor=answer_postprocessor,
        )
        gen_record = gen_records[0]
        if gen_record["status"] == GEN_STATUS_SKIPPED_QUOTA:
            stopped_reason = f"generation quota at: {question[:60]}"
            per_case.append({"question": question, "generation": gen_record})
            break
        if gen_record["status"] != GEN_STATUS_OK:
            stopped_reason = f"generation error at: {question[:60]}"
            per_case.append({"question": question, "generation": gen_record})
            break

        judge_records = run_judge_phase(
            selected_questions=[question],
            generation_records_by_question={question: gen_record},
            evidence_context_by_question={
                question: evidence_contexts[question]
            },
            ground_truth_by_question={
                q: GROUND_TRUTHS[q] for q in selected_questions
            },
            judge_model=PROBE_MODEL,
            judge_prompt_template_sha256=sha256_text(JUDGE_PROMPT_TEMPLATE),
            judge_fn=make_judge_call(judge_generator, tracker),
            checkpoint_store=judge_store,
            max_retries=1,
            sleep_fn=lambda seconds: None,
            judge_prompt_builder=build_production_judge_prompt,
            judge_max_tokens=PHASE2_MAX_TOKENS,
            judge_context_fingerprint=JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        )
        judge_record = judge_records[0]
        per_case.append({
            "question": question,
            "generation": gen_record,
            "judge": judge_record,
        })

        if judge_record["status"] == JUDGE_STATUS_SKIPPED_QUOTA:
            stopped_reason = f"judge quota at: {question[:60]}"
            break
        if judge_record["status"] not in {JUDGE_STATUS_OK}:
            if judge_record["status"] == JUDGE_STATUS_PARSE_INVALID:
                stopped_reason = f"judge invalid schema at: {question[:60]}"
                break
            stopped_reason = f"judge error at: {question[:60]}"
            break

    stored_judge = load_judge_records(args.judge_checkpoint)
    generation_records = [entry["generation"] for entry in per_case]
    raw_aggregate = build_official_aggregate(
        generation_records=generation_records,
        judge_records=list(stored_judge.values()),
    )
    aggregate = {
        **raw_aggregate,
        "official": False,
        "reason": (
            "forced false: quota probe subset with self-judge bias; "
            "never a benchmark"
        ),
    }

    case_summaries = []
    for entry in per_case:
        question = entry["question"]
        answer = entry["generation"].get("answer") or ""
        answer_integrity = audit_probe_answer(
            answer, evidence_contexts[question]
        )
        acceptance = build_probe_acceptance(
            question, answer, answer_integrity["citation_correctness"]
        )
        case_summaries.append({
            "question": question,
            "context_sha256": sha256_text(evidence_contexts[question]),
            "generation_status": entry["generation"]["status"],
            "answer": entry["generation"].get("answer"),
            **answer_integrity,
            "acceptance": acceptance,
            "judge_status": entry.get("judge", {}).get("status"),
            "scores": {
                key: entry["judge"]["scores"][key]
                for key in (
                    "faithfulness",
                    "answer_relevancy",
                    "context_precision",
                    "faithfulness_reason",
                    "relevancy_reason",
                    "precision_reason",
                )
            } if entry.get("judge") and entry["judge"]["status"] == JUDGE_STATUS_OK else None,
            "error": entry["generation"].get("error")
            or entry.get("judge", {}).get("error"),
        })

    acceptance_results = [
        case["acceptance"] for case in case_summaries
        if case["acceptance"] is not None
    ]
    provider_calls_complete = (
        stopped_reason is None
        and len(case_summaries) == len(selected_questions)
        and all(
            case["generation_status"] == GEN_STATUS_OK
            and case["judge_status"] == JUDGE_STATUS_OK
            for case in case_summaries
        )
    )
    quality_preflight_passed = (
        provider_calls_complete
        and all(case["integrity_passed"] for case in case_summaries)
        and all(result["passed"] for result in acceptance_results)
    )

    summary = {
        "probe": True,
        "official": False,
        "official_flag_source": (
            "forced false: quota probe subset with self-judge bias; never a benchmark"
        ),
        "model": PROBE_MODEL,
        "context_strategy": args.context_strategy,
        "self_judge_bias": (
            "generation and judging share one model; scores are directional only"
        ),
        "bound_artifact_fingerprint": args.expected_fingerprint,
        "binding": upstream.binding,
        "selected_questions": selected_questions,
        "stopped_reason": stopped_reason,
        "provider_calls_complete": provider_calls_complete,
        "quality_preflight_passed": quality_preflight_passed,
        "probe_acceptance_passed": quality_preflight_passed,
        "period_value_corrections": correction_rows,
        "token_usage_totals": tracker.totals,
        "aggregate_check": aggregate,
        "cases": case_summaries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    logger.info("Probe summary written: %s", args.output)
    return 0 if quality_preflight_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
