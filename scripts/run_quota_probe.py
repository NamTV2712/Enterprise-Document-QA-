"""Quota probe: exercise Phase 2A/2B on three cases only.

NOT a benchmark. This runner verifies the two-phase plumbing end to end
(parsing, checkpointing, binding, quota stop behavior) on a tiny subset
with explicit guardrails:

- model openai/gpt-oss-120b for BOTH generation and judging (self-judge
  bias is expected and results are never official)
- strictly sequential cases, one generation + one judge call each
  (judge allows at most one retry; generation none)
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

from src.evaluation.evaluator import (
    JUDGE_PROMPT_TEMPLATE,
    compute_citation_correctness,
)
from src.evaluation.generation_checkpoint import (
    GEN_STATUS_OK,
    GEN_STATUS_SKIPPED_QUOTA,
    GenerationCheckpointStore,
    GenerationUpstream,
    build_evidence_context,
    run_generation_phase,
    sha256_text,
)
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
    PHASE2_MAX_TOKENS,
    JUDGE_CONTEXT_BUILDER_FINGERPRINT,
    UsageTracker,
    build_production_judge_prompt,
    generation_pool_keys,
    judging_pool_keys,
    make_generation_call,
    make_judge_call,
)
from src.generation.generator import Generator
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:3f02a791b808310d3e9abd10dde7989fcce62e7474f60410ead844eddb14b86e"
)
GEN_CHECKPOINT_PATH = Path("data/eval_artifacts/probe_gen.jsonl")
JUDGE_CHECKPOINT_PATH = Path("data/eval_artifacts/probe_judge.jsonl")
SUMMARY_PATH = Path("data/eval_artifacts/probe_summary.json")

PROBE_MODEL = "openai/gpt-oss-120b"
PROBE_QUESTIONS = [
    "What was Apple's total net sales in fiscal year 2024?",
    "Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?",
    "How did Microsoft's total assets change year over year?",
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
}

COMPARATIVE_ACCEPTANCE_VALUES = ("391,035", "637,959")


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


def _load_artifact_and_binding() -> tuple[dict, GenerationUpstream]:
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Phase 1 artifact missing: {ARTIFACT_PATH}. Run "
            "scripts.run_evaluation_phase1 first."
        )
    raw_bytes = ARTIFACT_PATH.read_bytes()
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
    if embedded != EXPECTED_ARTIFACT_FINGERPRINT:
        raise RuntimeError(
            f"Artifact fingerprint drift: expected {EXPECTED_ARTIFACT_FINGERPRINT}, "
            f"found {embedded}. Refusing to bind the probe to unknown evidence."
        )
    file_sha = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    upstream = GenerationUpstream(
        artifact_path=ARTIFACT_PATH,
        artifact_sha256=file_sha,
        artifact_schema_version=artifact["schema_version"],
        model=PROBE_MODEL,
    )
    return artifact, upstream


def _generation_pool_keys() -> list[str]:
    return generation_pool_keys()


_usage_tracker = UsageTracker()


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
    args = parser.parse_args(argv)
    selected_questions = args.question or PROBE_QUESTIONS

    for path in (GEN_CHECKPOINT_PATH, JUDGE_CHECKPOINT_PATH):
        if args.fresh and path.exists():
            path.unlink()
            logger.info("Deleted stale probe checkpoint: %s", path)

    artifact, upstream = _load_artifact_and_binding()
    case_by_question = {case["question"]: case for case in artifact["cases"]}
    missing = [q for q in selected_questions if q not in case_by_question]
    if missing:
        raise RuntimeError(f"Probe questions absent from artifact: {missing}")

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
    generation_store = GenerationCheckpointStore(GEN_CHECKPOINT_PATH)
    judge_store = JudgeCheckpointStore(JUDGE_CHECKPOINT_PATH)

    per_case: list[dict] = []
    stopped_reason = None
    for question in selected_questions:
        logger.info("=== PROBE CASE: %s", question[:70])

        gen_records = run_generation_phase(
            selected_questions=[question],
            artifact_cases=case_by_question,
            upstream=upstream,
            generate_fn=make_generation_call(
                generation_generator, _usage_tracker
            ),
            checkpoint_store=generation_store,
            max_retries=0,
            sleep_fn=lambda seconds: None,
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
                question: build_evidence_context(case_by_question[question])
            },
            ground_truth_by_question={
                q: GROUND_TRUTHS[q] for q in selected_questions
            },
            judge_model=PROBE_MODEL,
            judge_prompt_template_sha256=sha256_text(JUDGE_PROMPT_TEMPLATE),
            judge_fn=make_judge_call(judge_generator, _usage_tracker),
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

    stored_judge = load_judge_records(JUDGE_CHECKPOINT_PATH)
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
        citation_correctness = compute_citation_correctness(
            answer,
            len(case_by_question[question]["final_chunk_ids"]),
        )
        case_summaries.append({
            "question": question,
            "generation_status": entry["generation"]["status"],
            "answer": entry["generation"].get("answer"),
            "citation_correctness": citation_correctness,
            "acceptance": build_probe_acceptance(
                question, answer, citation_correctness
            ),
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
    probe_acceptance_passed = (
        stopped_reason is None
        and all(result["passed"] for result in acceptance_results)
    )

    summary = {
        "probe": True,
        "official": False,
        "official_flag_source": (
            "forced false: quota probe subset with self-judge bias; never a benchmark"
        ),
        "model": PROBE_MODEL,
        "self_judge_bias": (
            "generation and judging share one model; scores are directional only"
        ),
        "bound_artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "binding": upstream.binding,
        "selected_questions": selected_questions,
        "stopped_reason": stopped_reason,
        "probe_acceptance_passed": probe_acceptance_passed,
        "token_usage_totals": _usage_tracker.totals,
        "aggregate_check": aggregate,
        "cases": case_summaries,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    logger.info("Probe summary written: %s", SUMMARY_PATH)
    return 0 if probe_acceptance_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
