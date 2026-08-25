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
import time
from pathlib import Path

from configs.settings import settings
from src.evaluation.evaluator import (
    JUDGE_PROMPT_TEMPLATE,
    JUDGE_SYSTEM_PROMPT,
    JudgeParseError,
    _extract_relevant_window,
    _parse_judge_response,
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
    JudgeParseErrorStub,
    build_official_aggregate,
    load_judge_records,
    run_judge_phase,
)
from src.generation.generator import SYSTEM_PROMPT, Generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:f1129d814274e95d3b2019aa58ef840fc28817c1d82b548a613e2de697986841"
)
GEN_CHECKPOINT_PATH = Path("data/eval_artifacts/probe_gen.jsonl")
JUDGE_CHECKPOINT_PATH = Path("data/eval_artifacts/probe_judge.jsonl")
SUMMARY_PATH = Path("data/eval_artifacts/probe_summary.json")

PROBE_MODEL = "openai/gpt-oss-120b"
PROBE_QUESTIONS = [
    "What was Apple's total net sales in fiscal year 2024?",
    "Which company, Apple or Amazon, has higher total revenue?",
    "How did Microsoft's total assets change year over year?",
]
GROUND_TRUTHS = {
    PROBE_QUESTIONS[0]: (
        "Apple's total net sales in fiscal year 2024 were $391,035 million."
    ),
    PROBE_QUESTIONS[1]: (
        "Amazon's consolidated net sales are significantly higher than "
        "Apple's total net sales."
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

    The original test question is year-ambiguous, while the approved probe
    acceptance pins the FY2024 figures. Keep that distinction visible instead
    of silently treating a correct latest-year comparison as the requested
    FY2024 answer.
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
    keys = [settings.groq_api_key_fall_back, settings.groq_api_key_fall_back2]
    if not any(keys):
        keys = [settings.groq_api_key, settings.groq_api_key2]
    return keys


def _make_generation_call(generator: Generator):
    def generate(prompt: str) -> str:
        started = time.perf_counter()
        response = generator._create_groq_chat_completion(
            model=generator.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            temperature=0,
        )
        elapsed = time.perf_counter() - started
        usage = getattr(response, "usage", None)
        _record_usage("generation", usage, elapsed)
        return response.choices[0].message.content or ""

    return generate


def _make_judge_call(generator: Generator):
    def judge(prompt: str) -> dict:
        started = time.perf_counter()
        # gpt-oss-120b writes longer rationales than the legacy 70B; the
        # production 320-token cap truncated its JSON mid-object during the
        # first probe pass, so the probe budgets generously here instead.
        response = generator._create_groq_chat_completion(
            model=generator.model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            temperature=0,
        )
        elapsed = time.perf_counter() - started
        usage = getattr(response, "usage", None)
        _record_usage("judging", usage, elapsed)
        raw = response.choices[0].message.content or ""
        try:
            return _parse_judge_response(raw)
        except JudgeParseError as parse_error:
            raise JudgeParseErrorStub(str(parse_error)) from parse_error

    return judge


def build_production_judge_prompt(
    question: str, answer: str, evidence_context: str, ground_truth: str
) -> str:
    """Production judging instructions over the frozen evidence blocks."""
    context_texts = [
        block.split("\n", 1)[1]
        for block in evidence_context.split("\n\n")
        if "\n" in block
    ]
    context_str = "\n\n".join(
        f"[Chunk {i+1}]: {_extract_relevant_window(text, question)}"
        for i, text in enumerate(context_texts)
    )
    return JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        ground_truth=ground_truth,
        context_str=context_str,
        answer=answer,
    )


_USAGE_TOTALS: dict[str, int] = {
    "generation_prompt_tokens": 0,
    "generation_completion_tokens": 0,
    "judging_prompt_tokens": 0,
    "judging_completion_tokens": 0,
}


def _record_usage(phase: str, usage, elapsed: float) -> None:
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    if prompt_tokens is not None:
        _USAGE_TOTALS[f"{phase}_prompt_tokens"] += int(prompt_tokens)
    if completion_tokens is not None:
        _USAGE_TOTALS[f"{phase}_completion_tokens"] += int(completion_tokens)
    logger.info(
        "%s call done in %.2fs (prompt=%s, completion=%s tokens)",
        phase,
        elapsed,
        prompt_tokens,
        completion_tokens,
    )


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
    judge_generator = Generator(model=PROBE_MODEL)
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
            generate_fn=_make_generation_call(generation_generator),
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
            judge_fn=_make_judge_call(judge_generator),
            checkpoint_store=judge_store,
            max_retries=1,
            sleep_fn=lambda seconds: None,
            judge_prompt_builder=build_production_judge_prompt,
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
        "token_usage_totals": _USAGE_TOTALS,
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
