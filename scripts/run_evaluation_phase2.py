"""Evaluation Phase 2: frozen-evidence generation and judging, full set.

Consumes ONLY the Phase 1 artifact — retrieval never reruns here. Every
generation/judge record is checkpointed against the artifact binding, so
interrupted runs resume without mixing evidence, prompts, or models.

The provider run is complete only when every selected case completes both
phases with OK status under one shared binding (see
``judge_checkpoint.build_official_aggregate`` plus the explicit coverage
check in ``run_phase2``). A complete run written to the protected official
path is marked ``official=true``; a complete candidate run remains
``official=false`` until a separate admission decision promotes it. Any
quota skip, provider error, invalid judge schema, or early stop forces a
nonzero exit; partial output must never be published as a benchmark.

Usage:
    python -m scripts.run_evaluation_phase2 --priority 2 --fresh
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from src.evaluation.evaluator import (
    JUDGE_PROMPT_TEMPLATE,
    check_fallback_correctness,
    compute_citation_correctness,
    compute_recall_proxy,
)
from src.evaluation.generation_checkpoint import (
    GEN_STATUS_OK,
    GenerationCheckpointStore,
    GenerationUpstream,
    build_evidence_context,
    parse_evidence_context,
    run_generation_phase,
    sha256_text,
)
from src.evaluation.judge_checkpoint import (
    JUDGE_STATUS_OK,
    JUDGE_STATUS_PARSE_INVALID,
    JUDGE_STATUS_SKIPPED_QUOTA,
    JudgeCheckpointStore,
    build_official_aggregate,
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
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_COMPARATIVE_V3,
    CONTEXT_STRATEGY_COMPARATIVE_V5,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    CONTEXT_STRATEGY_ROUTE_AWARE,
    CONTEXT_STRATEGY_SELECTIVE,
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V4,
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import Generator
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EVAL_MODEL = "openai/gpt-oss-120b"
ARTIFACT_PATH = Path("data/eval_artifacts/phase1_priority2.json")
# Must match scripts.run_quota_probe.EXPECTED_ARTIFACT_FINGERPRINT; both
# runners refuse to bind to any other frozen evidence.
EXPECTED_ARTIFACT_FINGERPRINT = (
    "sha256:1ad021ce72af2116f9b4f7ad780d5c6e809fd5a01e46d30d0ae4bfecd62599d9"
)
GEN_CHECKPOINT_PATH = Path("data/eval_artifacts/phase2_gen.jsonl")
JUDGE_CHECKPOINT_PATH = Path("data/eval_artifacts/phase2_judge.jsonl")
RESULTS_PATH = Path("data/eval_artifacts/phase2_results.json")
# This is the immutable reference result used for admission comparisons. A
# fresh candidate run must write to an explicit candidate path instead of
# deleting or replacing this file by accident.
OFFICIAL_SELECTIVE_V2_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)

RESULTS_SCHEMA_VERSION = 1

REPRODUCIBILITY_AUDITS = {
    "context_precision_reproducibility",
    "enumeration_context_reproducibility",
    "enumeration_answer_completion_reproducibility",
    "grounded_completion_v3_reproducibility",
    "fact_evidence_sufficiency_reproducibility_v1",
}
UNIFIED_COMPLETION_REPRODUCIBILITY_AUDITS = {
    "enumeration_answer_completion_reproducibility",
}
# These strategies have already passed the provider-free admission contract and
# are allowed as stable runner defaults without an experimental sentinel.
ADMITTED_CONTEXT_STRATEGIES = {
    CONTEXT_STRATEGY_SELECTIVE_V2,
    CONTEXT_STRATEGY_SELECTIVE_V5,
}

_JUDGE_SCORE_KEYS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
)


def assert_phase2_retrieval_hermeticity() -> None:
    """Reject loaded retrieval executors before touching frozen evidence."""
    # Imports used only for artifact provenance or type definitions are safe.
    # Hybrid retrieval, corpus loaders, and manifests would indicate Phase 2
    # is no longer consuming frozen evidence only.
    allowed_modules = {
        "src.retrieval",
        "src.retrieval.query_shaper",
        "src.retrieval.lexical_ladder",
        "src.retrieval.retriever",
        "src.retrieval.embedder",
        "src.retrieval.vector_store",
    }
    forbidden = [
        name for name in sys.modules
        if name.startswith("src.retrieval") and name not in allowed_modules
    ]
    if forbidden:
        raise RuntimeError(f"Retrieval machinery loaded in phase 2: {forbidden}")


def load_bound_artifact(
    artifact_path: Path,
    expected_fingerprint: str,
    context_strategy: str = CONTEXT_STRATEGY_FULL_EVIDENCE,
) -> tuple[dict[str, Any], GenerationUpstream]:
    """Load the artifact and refuse any fingerprint drift."""
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Phase 1 artifact missing: {artifact_path}. Run "
            "scripts.run_evaluation_phase1 first."
        )
    raw_bytes = artifact_path.read_bytes()
    artifact = json.loads(raw_bytes.decode("utf-8"))
    shaper_fingerprint = artifact["fingerprints"].get("query_shaper")
    if shaper_fingerprint != QUERY_SHAPER_FINGERPRINT:
        raise RuntimeError(
            "Query-shaper provenance drift: Phase 1 artifact is missing the "
            "current deterministic shaper fingerprint. Rebuild Phase 1 before "
            "running Phase 2."
        )
    if artifact["fingerprints"].get("lexical_ladder") != LEXICAL_LADDER_FINGERPRINT:
        raise RuntimeError(
            "Lexical-ladder provenance drift: rebuild Phase 1 before running "
            "Phase 2."
        )
    embedded = artifact["fingerprints"]["artifact"]
    if embedded != expected_fingerprint:
        raise RuntimeError(
            f"Artifact fingerprint drift: expected {expected_fingerprint}, "
            f"found {embedded}. Rebuild the artifact or update the pin; "
            "refusing to bind official results to unknown evidence."
        )
    file_sha = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    upstream = GenerationUpstream(
        artifact_path=artifact_path,
        artifact_sha256=file_sha,
        artifact_schema_version=artifact["schema_version"],
        model=EVAL_MODEL,
        system_prompt_sha256=GENERATION_SYSTEM_PROMPT_FINGERPRINT,
        context_strategy=context_strategy,
    )
    return artifact, upstream


def select_questions(
    artifact: dict[str, Any], priority: int
) -> list[TestCase]:
    """Selected test cases whose frozen evidence exists in the artifact."""
    case_by_question = {
        case["question"]: case for case in artifact["cases"]
    }
    selected = [tc for tc in TEST_SET if tc.priority <= priority]
    missing = [
        tc.question for tc in selected if tc.question not in case_by_question
    ]
    if missing:
        raise RuntimeError(
            "Artifact lacks evidence for selected questions: "
            f"{sorted(missing)}"
        )
    return selected


def require_reproducibility_report(
    report_path: Path | None,
    candidate_strategy: str,
) -> None:
    """Require a passed all-replicates gate before a candidate N=30 run."""
    if report_path is None:
        raise SystemExit(
            "Candidate priority-2 runs require --reproducibility-report "
            "from a passed reproducibility diagnostic."
        )
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Cannot read reproducibility report {report_path}: {exc}"
        ) from exc
    rule = payload.get("pre_registered_rule") or {}
    gates = payload.get("gates") or {}
    if not (
        payload.get("audit") in REPRODUCIBILITY_AUDITS
        and payload.get("passed") is True
        and payload.get("candidate_strategy") == candidate_strategy
        and rule.get("minimum_replicates", 0) >= 2
        and rule.get("required_pass_rate") == 1.0
        and rule.get("best_of_selection_forbidden") is True
        and gates.get("all_replicates_pass") is True
        and (
            payload.get("audit")
            not in UNIFIED_COMPLETION_REPRODUCIBILITY_AUDITS
            or ANSWER_COMPLETION_FINGERPRINT
            in (payload.get("completion_fingerprints") or [])
        )
    ):
        raise SystemExit(
            "Reproducibility gate failed or does not match candidate strategy; "
            "refusing candidate priority-2 run."
        )


def unique_evidence_texts(case_payload: dict[str, Any]) -> list[str]:
    """Deduplicated chunk texts in deterministic source order."""
    texts: list[str] = []
    seen: set[str] = set()
    for query_entry in case_payload.get("queries", []):
        for chunk in query_entry.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            texts.append(chunk.get("text", ""))
    return texts


def compute_case_metrics(
    case_payload: dict[str, Any],
    answer: str,
    required_keywords: list[str],
    expects_fallback: bool,
    evidence_context: str | None = None,
) -> dict[str, Any]:
    """Deterministic per-case checks over frozen evidence + the answer."""
    rendered_context = (
        evidence_context
        if evidence_context is not None
        else build_evidence_context(case_payload)
    )
    source_blocks = parse_evidence_context(rendered_context)
    citation_correctness = compute_citation_correctness(
        answer, len(source_blocks)
    )
    chunks = [
        SimpleNamespace(text=block["text"])
        for block in source_blocks
    ]
    recall_proxy = compute_recall_proxy(required_keywords, chunks)
    fallback_correct = check_fallback_correctness(answer, expects_fallback)
    return {
        "citation_correctness": citation_correctness,
        "recall_proxy": recall_proxy,
        "fallback_correct": fallback_correct,
    }


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def aggregate_scores(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Judge averages plus a category table over OK judged records only."""
    ok = [
        r for r in records
        if r.get("status") == JUDGE_STATUS_OK
        and isinstance(r.get("scores"), dict)
    ]
    metrics: dict[str, float | None] = {}
    for key in _JUDGE_SCORE_KEYS:
        values = [
            float(r["scores"][key]) for r in ok
            if isinstance(r["scores"].get(key), (int, float))
        ]
        metrics[key] = _mean(values)
    overall = (
        round(
            sum(metrics[key] for key in _JUDGE_SCORE_KEYS)
            / len(_JUDGE_SCORE_KEYS),
            4,
        ) if all(v is not None for v in metrics.values()) else None
    )

    by_category: dict[str, list[dict[str, Any]]] = {}
    for record in ok:
        by_category.setdefault(record.get("category", ""), []).append(record)

    category_table: dict[str, dict[str, Any]] = {}
    for category, cat_records in sorted(by_category.items()):
        entry: dict[str, Any] = {"num_cases": len(cat_records)}
        for key in _JUDGE_SCORE_KEYS:
            values = [
                float(r["scores"][key]) for r in cat_records
                if isinstance(r["scores"].get(key), (int, float))
            ]
            entry[key] = _mean(values)
        category_table[category] = entry

    return {
        "num_judged_ok": len(ok),
        **metrics,
        "overall_judge_average": overall,
        "categories": category_table,
    }


def aggregate_deterministic(
    metric_rows: list[dict[str, Any]],
) -> dict[str, float | None]:
    """Averages for the deterministic checks over generation-OK cases."""
    citations = [
        row["citation_correctness"] for row in metric_rows
        if row["citation_correctness"] is not None
    ]
    recalls = [
        row["recall_proxy"] for row in metric_rows
        if row["recall_proxy"] is not None
    ]
    fallback_accuracy = (
        round(
            sum(1 for row in metric_rows if row["fallback_correct"])
            / len(metric_rows),
            4,
        ) if metric_rows else None
    )
    return {
        "citation_correctness_avg": _mean(citations),
        "recall_proxy_avg": _mean(recalls),
        "fallback_accuracy": fallback_accuracy,
        "num_citation_scored": len(citations),
        "num_recall_scored": len(recalls),
    }


def run_phase2(
    *,
    selected: list[TestCase],
    case_by_question: dict[str, dict[str, Any]],
    upstream: GenerationUpstream,
    bound_fingerprint: str,
    generate_fn: Callable[[str], str],
    judge_fn: Callable[[str], dict],
    generation_store: GenerationCheckpointStore,
    judge_store: JudgeCheckpointStore,
    max_gen_retries: int = 2,
    max_judge_retries: int = 2,
    sleep_fn: Callable[[float], None] = time.sleep,
    evidence_context_fn: Callable[[dict], str] | None = None,
    answer_postprocessor: Callable[[str, str, str], str] | None = None,
    answer_completion_metadata: dict[str, dict[str, Any]] | None = None,
    publish_official: bool = True,
) -> dict[str, Any]:
    """Execute both phases sequentially and compose the results payload.

    ``generate_fn``/``judge_fn`` are the only provider touchpoints.
    ``evidence_context_fn`` renders a case payload into prompt blocks;
    it defaults to full-evidence rendering and is shared by generation
    and judging. The renderer fingerprint and upstream ``context_strategy``
    both participate in the binding, so stale or mixed contexts cannot resume.
    Quota or hard failures stop the whole run immediately after
    checkpointing so remaining quota is not burned against a dead run.
    """
    render_context = evidence_context_fn or build_evidence_context
    tracker = UsageTracker()
    meta_by_question = {tc.question: tc for tc in selected}
    # Render each case once. The exact same byte string is then passed to
    # generation, deterministic metrics, and judging, preventing a renderer
    # drift from producing three subtly different evidence views.
    rendered_context_by_question = {
        tc.question: render_context(case_by_question[tc.question])
        for tc in selected
    }

    def context_for(case_payload: dict[str, Any]) -> str:
        question = case_payload.get("question")
        if question not in rendered_context_by_question:
            raise KeyError(f"No rendered context for question: {question!r}")
        return rendered_context_by_question[question]

    generation_records: list[dict[str, Any]] = []
    judge_records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    stopped_reason: str | None = None

    for tc in selected:
        records = run_generation_phase(
            selected_questions=[tc.question],
            artifact_cases=case_by_question,
            upstream=upstream,
            generate_fn=generate_fn,
            checkpoint_store=generation_store,
            max_retries=max_gen_retries,
            sleep_fn=sleep_fn,
            evidence_context_fn=context_for,
            answer_postprocessor=answer_postprocessor,
            answer_completion_metadata=answer_completion_metadata,
        )
        gen_record = records[0]
        generation_records.append({**gen_record, "question": tc.question})
        if gen_record["status"] != GEN_STATUS_OK:
            stopped_reason = (
                f"generation {gen_record['status']} at: {tc.question[:60]}"
            )
            logger.error("Stopping before judging: %s", stopped_reason)
            break
        metric_rows.append({
            **compute_case_metrics(
                case_by_question[tc.question],
                gen_record["answer"],
                tc.required_keywords,
                tc.expects_fallback,
                evidence_context=rendered_context_by_question[tc.question],
            ),
            "question": tc.question,
        })

    if stopped_reason is None:
        ok_generations = [
            r for r in generation_records if r["status"] == GEN_STATUS_OK
        ]
        for question_record in ok_generations:
            question = question_record["question"]
            tc = meta_by_question[question]
            judge_out = run_judge_phase(
                selected_questions=[question],
                generation_records_by_question={question: question_record},
                evidence_context_by_question={
                    question: rendered_context_by_question[question]
                },
                ground_truth_by_question={
                    question: tc.ground_truth
                },
                judge_model=EVAL_MODEL,
                judge_prompt_template_sha256=sha256_text(
                    JUDGE_PROMPT_TEMPLATE
                ),
                judge_fn=judge_fn,
                checkpoint_store=judge_store,
                max_retries=max_judge_retries,
                sleep_fn=sleep_fn,
                judge_prompt_builder=build_production_judge_prompt,
                judge_max_tokens=PHASE2_MAX_TOKENS,
                judge_context_fingerprint=JUDGE_CONTEXT_BUILDER_FINGERPRINT,
            )
            judge_record = judge_out[0]
            judge_records.append({
                **judge_record,
                "question": question,
                "category": tc.category,
            })
            if judge_record["status"] == JUDGE_STATUS_SKIPPED_QUOTA:
                stopped_reason = f"judge quota at: {question[:60]}"
                break
            if judge_record["status"] == JUDGE_STATUS_PARSE_INVALID:
                stopped_reason = f"judge invalid schema at: {question[:60]}"
                break
            if judge_record["status"] != JUDGE_STATUS_OK:
                stopped_reason = f"judge error at: {question[:60]}"
                break

    aggregate = build_official_aggregate(
        generation_records=generation_records,
        judge_records=judge_records,
    )
    # Explicit completeness gate: an early stop leaves later questions
    # without any record, which build_official_aggregate cannot see.
    complete = (
        len(generation_records) == len(selected)
        and all(
            r["status"] == GEN_STATUS_OK for r in generation_records
        )
        and len([
            r for r in judge_records if r["status"] == JUDGE_STATUS_OK
        ]) == len(selected)
        and stopped_reason is None
    )
    benchmark_eligible = bool(aggregate.get("official")) and complete
    official = benchmark_eligible and publish_official
    if benchmark_eligible and not publish_official:
        reason = (
            "provider-complete candidate: not published as official; "
            "run the separate admission audit before promotion"
        )
    else:
        reason = aggregate.get("reason") if not official else ""
    if not official and not reason:
        reason = (
            f"incomplete run: stopped_reason={stopped_reason!r}, "
            f"generation_records={len(generation_records)}/{len(selected)}"
        )

    cases: list[dict[str, Any]] = []
    metric_by_question = {row.pop("question"): row for row in metric_rows}
    gen_by_question = {r["question"]: r for r in generation_records}
    judge_by_question = {r["question"]: r for r in judge_records}
    for tc in selected:
        gen_record = gen_by_question.get(tc.question)
        judge_record = judge_by_question.get(tc.question)
        case_entry: dict[str, Any] = {
            "question": tc.question,
            "category": tc.category,
            "route": "decomposed" if tc.expects_decomposition else "direct",
            "generation_status": (
                gen_record["status"] if gen_record else "NOT_RUN"
            ),
            "judge_status": (
                judge_record["status"] if judge_record else "NOT_RUN"
            ),
            "answer": (gen_record or {}).get("answer"),
            "error": (gen_record or {}).get("error")
            or (judge_record or {}).get("error"),
            "deterministic": metric_by_question.get(tc.question),
            "scores": (
                {key: judge_record["scores"][key] for key in _JUDGE_SCORE_KEYS}
                if judge_record and judge_record.get("status") == JUDGE_STATUS_OK
                else None
            ),
        }
        cases.append(case_entry)

    return {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "official": official,
        "provider_complete": complete,
        "benchmark_eligible": benchmark_eligible,
        "reason": reason,
        "model": EVAL_MODEL,
        "judge_model": EVAL_MODEL,
        "context_strategy": upstream.context_strategy,
        "num_selected": len(selected),
        "num_generation_ok": sum(
            1 for r in generation_records if r["status"] == GEN_STATUS_OK
        ),
        "num_judged_ok": sum(
            1 for r in judge_records if r["status"] == JUDGE_STATUS_OK
        ),
        "stopped_reason": stopped_reason,
        "binding": upstream.binding,
        "upstream_artifact_sha256": upstream.artifact_sha256,
        "bound_artifact_fingerprint": bound_fingerprint,
        "token_usage_totals": tracker.totals,
        "metrics": aggregate_scores(judge_records),
        "deterministic": aggregate_deterministic(metric_rows),
        "period_value_corrections": answer_completion_metadata or {},
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--priority", type=int, default=2)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument(
        "--expected-fingerprint",
        default=EXPECTED_ARTIFACT_FINGERPRINT,
        help="Embedded artifact fingerprint the run binds to.",
    )
    parser.add_argument(
        "--gen-checkpoint",
        type=Path,
        default=None,
        help="Override the generation checkpoint path (strategy-aware default).",
    )
    parser.add_argument(
        "--judge-checkpoint",
        type=Path,
        default=None,
        help="Override the judge checkpoint path (strategy-aware default).",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--reproducibility-report",
        type=Path,
        default=None,
        help=(
            "Passed all-replicates sentinel report required before a "
            "priority-2 experimental packing run."
        ),
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete existing checkpoints and results before running.",
    )
    parser.add_argument("--max-gen-retries", type=int, default=2)
    parser.add_argument("--max-judge-retries", type=int, default=2)
    parser.add_argument(
        "--allow-official-overwrite",
        action="store_true",
        help=(
            "Explicitly allow writing the protected official selective-v2 "
            "result path. Candidate/admission runs must omit this flag."
        ),
    )
    parser.add_argument(
        "--context-strategy",
        choices=[
            CONTEXT_STRATEGY_FULL_EVIDENCE,
            CONTEXT_STRATEGY_ROUTE_AWARE,
            CONTEXT_STRATEGY_SELECTIVE,
            CONTEXT_STRATEGY_COMPARATIVE_V3,
            CONTEXT_STRATEGY_COMPARATIVE_V5,
            CONTEXT_STRATEGY_SELECTIVE_V2,
            CONTEXT_STRATEGY_SELECTIVE_V4,
            CONTEXT_STRATEGY_SELECTIVE_V5,
            CONTEXT_STRATEGY_SELECTIVE_V6,
        ],
        default=CONTEXT_STRATEGY_SELECTIVE_V5,
        help=(
            "selective_packed_v5_enumeration_candidate is the admitted default: "
            "it preserves the selective-v2 policy while using the gated "
            "enumeration consensus selector. selective_packed_v2, "
            "selective_packed_v1, full_evidence_v1, comparative_packed_v3, "
            "and comparative_oracle_free_v5 remain available for replay."
        ),
    )
    args = parser.parse_args(argv)

    packed_mode = args.context_strategy != CONTEXT_STRATEGY_FULL_EVIDENCE
    suffix = {
        CONTEXT_STRATEGY_ROUTE_AWARE: "_packed",
        CONTEXT_STRATEGY_SELECTIVE: "_packed_selective",
        CONTEXT_STRATEGY_COMPARATIVE_V3: "_packed_comparative_v3",
            CONTEXT_STRATEGY_COMPARATIVE_V5: "_packed_comparative_v5",
            CONTEXT_STRATEGY_SELECTIVE_V2: "_packed_selective_v2",
            CONTEXT_STRATEGY_SELECTIVE_V4: "_packed_selective_v4",
            CONTEXT_STRATEGY_SELECTIVE_V5: "_packed_selective_v5_enumeration",
            CONTEXT_STRATEGY_SELECTIVE_V6: "_packed_selective_v6_fact",
    }.get(args.context_strategy, "")
    if args.gen_checkpoint is None:
        args.gen_checkpoint = Path(
            str(GEN_CHECKPOINT_PATH).replace(".jsonl", f"{suffix}.jsonl")
        )
    if args.judge_checkpoint is None:
        args.judge_checkpoint = Path(
            str(JUDGE_CHECKPOINT_PATH).replace(".jsonl", f"{suffix}.jsonl")
        )
    if args.output is None:
        args.output = Path(str(RESULTS_PATH).replace(".json", f"{suffix}.json"))

    assert_phase2_retrieval_hermeticity()

    try:
        output_is_official = (
            args.output.resolve()
            == OFFICIAL_SELECTIVE_V2_RESULTS_PATH.resolve()
        )
    except OSError:
        output_is_official = args.output == OFFICIAL_SELECTIVE_V2_RESULTS_PATH
    if output_is_official and not args.allow_official_overwrite:
        raise SystemExit(
            "Refusing to write the protected official selective-v2 result. "
            "Pass an explicit candidate --output path; the official result "
            "is changed only after a separate admission audit."
        )

    if (
        args.priority >= 2
        and args.context_strategy not in ADMITTED_CONTEXT_STRATEGIES
        and args.context_strategy != CONTEXT_STRATEGY_FULL_EVIDENCE
        and not output_is_official
    ):
        require_reproducibility_report(
            args.reproducibility_report,
            args.context_strategy,
        )

    for path in (args.gen_checkpoint, args.judge_checkpoint, args.output):
        if args.fresh and path.exists():
            path.unlink()
            logger.info("Deleted stale evaluation file: %s", path)

    artifact, upstream = load_bound_artifact(
        args.artifact, args.expected_fingerprint, args.context_strategy
    )
    selected = select_questions(artifact, args.priority)
    case_by_question = {
        case["question"]: case for case in artifact["cases"]
    }
    meta_by_question = {tc.question: tc for tc in selected}
    evidence_context_fn: Callable[[dict], str] | None = None
    if packed_mode:
        def evidence_context_fn(case_payload: dict) -> str:
            return render_case_context(
                case_payload,
                required_keywords=meta_by_question[
                    case_payload["question"]
                ].required_keywords,
                strategy=args.context_strategy,
            )

    logger.info(
        "Phase 2 over %d cases bound to %s (strategy=%s)",
        len(selected), args.artifact, args.context_strategy,
    )

    generation_generator = Generator(
        model=EVAL_MODEL, api_keys=generation_pool_keys()
    )
    judge_generator = Generator(model=EVAL_MODEL, api_keys=judging_pool_keys())
    tracker = UsageTracker()
    generation_call = make_generation_call(generation_generator, tracker)
    correction_rows: dict[str, dict[str, Any]] = {}
    if args.output.exists() and not args.fresh:
        try:
            previous = json.loads(args.output.read_text(encoding="utf-8"))
            if previous.get("binding") == upstream.binding:
                previous_rows = previous.get("period_value_corrections") or {}
                if isinstance(previous_rows, dict):
                    correction_rows.update(previous_rows)
        except (OSError, json.JSONDecodeError):
            logger.warning("Ignoring unreadable prior Phase 2 summary: %s", args.output)

    summary = run_phase2(
        selected=selected,
        case_by_question=case_by_question,
        upstream=upstream,
        bound_fingerprint=args.expected_fingerprint,
        generate_fn=generation_call,
        judge_fn=make_judge_call(judge_generator, tracker),
        generation_store=GenerationCheckpointStore(args.gen_checkpoint),
        judge_store=JudgeCheckpointStore(args.judge_checkpoint),
        max_gen_retries=args.max_gen_retries,
        max_judge_retries=args.max_judge_retries,
        evidence_context_fn=evidence_context_fn,
        answer_postprocessor=make_answer_completion_postprocessor(
            generation_call, correction_rows
        ),
        answer_completion_metadata=correction_rows,
        publish_official=output_is_official,
    )
    summary["token_usage_totals"] = tracker.totals

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== Phase 2 summary ===")
    print(f"  official           : {summary['official']}")
    print(f"  reason             : {summary['reason']}")
    print(f"  selected           : {summary['num_selected']}")
    print(f"  generation OK      : {summary['num_generation_ok']}")
    print(f"  judged OK          : {summary['num_judged_ok']}")
    print(f"  stopped_reason     : {summary['stopped_reason']}")
    metrics = summary["metrics"]
    for key in (*_JUDGE_SCORE_KEYS, "overall_judge_average"):
        print(f"  {key:<19}: {metrics[key]}")
    print(f"  Results written    : {args.output}")

    return 0 if summary["provider_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
