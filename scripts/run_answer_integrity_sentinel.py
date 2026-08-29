"""Run the six answer-integrity sentinel cases against frozen evidence.

This is a quota-gated, non-official provider run. It uses separate checkpoint
files and compares deterministic answer-contract findings with the baseline
Phase 2 answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from src.evaluation.answer_contract import audit_answer, render_source_texts
from src.evaluation.evaluator import JUDGE_PROMPT_TEMPLATE
from src.evaluation.generation_checkpoint import (
    GenerationCheckpointStore,
    GenerationUpstream,
    build_evidence_context,
    run_generation_phase,
    sha256_text,
)
from src.evaluation.judge_checkpoint import (
    JUDGE_STATUS_OK,
    JudgeCheckpointStore,
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
from src.evaluation.test_set import TEST_SET
from src.generation.generator import Generator
from src.retrieval.lexical_ladder import LEXICAL_LADDER_FINGERPRINT
from src.retrieval.query_shaper import QUERY_SHAPER_FINGERPRINT


ARTIFACT = Path("data/eval_artifacts/phase1_priority2.json")
BASELINE = Path("data/eval_artifacts/phase2_results_packed_selective.json")
GEN_CHECKPOINT = Path("data/eval_artifacts/answer_sentinel_gen.jsonl")
JUDGE_CHECKPOINT = Path("data/eval_artifacts/answer_sentinel_judge.jsonl")
SUMMARY = Path("data/eval_artifacts/answer_sentinel_summary.json")
MODEL = "openai/gpt-oss-120b"
QUESTIONS = [
    "How did Amazon's AWS net sales change from 2024 to 2025?",
    "How did Microsoft's total assets change year over year?",
    "How does Amazon's AWS segment compare to Microsoft's cloud business in terms of growth?",
    "What risks does Amazon face related to its international operations?",
    "Which company depends more on cloud/subscription revenue, Microsoft or Apple?",
    "Who audited Apple's financial statements and when was the report signed?",
]


def _load() -> tuple[dict, GenerationUpstream]:
    raw = ARTIFACT.read_bytes()
    artifact = json.loads(raw.decode("utf-8"))
    expected = "sha256:8283b628bb755b00bef86a26d7c608f9b385836c28dad588992b7d533ea51ee4"
    if artifact["fingerprints"]["artifact"] != expected:
        raise RuntimeError("Phase 1 artifact fingerprint drift")
    if artifact["fingerprints"].get("query_shaper") != QUERY_SHAPER_FINGERPRINT:
        raise RuntimeError("Phase 1 artifact lacks current query-shaper provenance")
    if artifact["fingerprints"].get("lexical_ladder") != LEXICAL_LADDER_FINGERPRINT:
        raise RuntimeError("Phase 1 artifact lacks current lexical-ladder provenance")
    upstream = GenerationUpstream(
        artifact_path=ARTIFACT,
        artifact_sha256=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        artifact_schema_version=artifact["schema_version"],
        model=MODEL,
        context_strategy="selective_packed_v1",
    )
    return artifact, upstream


def _baseline() -> dict[str, dict]:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    return {case["question"]: case for case in data["cases"]}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if args.fresh:
        for path in (GEN_CHECKPOINT, JUDGE_CHECKPOINT, SUMMARY):
            if path.exists():
                path.unlink()

    artifact, upstream = _load()
    cases = {case["question"]: case for case in artifact["cases"]}
    truths = {case.question: case.ground_truth for case in TEST_SET}
    tracker = UsageTracker()
    generation = Generator(model=MODEL, api_keys=generation_pool_keys())
    judge = Generator(model=MODEL, api_keys=judging_pool_keys())
    gen_store = GenerationCheckpointStore(GEN_CHECKPOINT)
    judge_store = JudgeCheckpointStore(JUDGE_CHECKPOINT)
    rows = []

    for question in QUESTIONS:
        gen_record = run_generation_phase(
            [question], cases, upstream,
            make_generation_call(generation, tracker), gen_store,
            max_retries=0, sleep_fn=lambda _: None,
        )[0]
        if gen_record.get("status") != "OK":
            rows.append({"question": question, "generation": gen_record})
            continue
        judge_record = run_judge_phase(
            [question], {question: gen_record},
            {question: build_evidence_context(cases[question])},
            {question: truths[question]}, MODEL,
            sha256_text(JUDGE_PROMPT_TEMPLATE),
            make_judge_call(judge, tracker), judge_store,
            max_retries=1, sleep_fn=lambda _: None,
            judge_prompt_builder=build_production_judge_prompt,
            judge_max_tokens=PHASE2_MAX_TOKENS,
            judge_context_fingerprint=JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        )[0]
        audit = audit_answer(
            gen_record.get("answer") or "", render_source_texts(cases[question])
        )
        baseline = _baseline()[question]
        baseline_audit = audit_answer(
            baseline.get("answer") or "", render_source_texts(cases[question])
        )
        rows.append({
            "question": question,
            "answer": gen_record.get("answer"),
            "generation_status": gen_record.get("status"),
            "judge_status": judge_record.get("status"),
            "scores": judge_record.get("scores"),
            "audit": audit.to_dict(),
            "baseline_audit": baseline_audit.to_dict(),
            "gate": {
                "legacy_citations_removed": audit.malformed_line_citations == 0,
                "uncited_removed": not audit.uncited_answer,
                "numeric_flags_not_increased": len(audit.unsupported_numeric_claims)
                <= len(baseline_audit.unsupported_numeric_claims),
            },
        })

    completed = [row for row in rows if row.get("judge_status") == JUDGE_STATUS_OK]
    gates = [row["gate"] for row in completed if "gate" in row]
    report = {
        "official": False,
        "reason": "sentinel subset; not a benchmark",
        "model": MODEL,
        "questions": QUESTIONS,
        "num_completed": len(completed),
        "all_provider_calls_ok": len(completed) == len(QUESTIONS),
        "gate_passed": bool(gates) and all(all(g.values()) for g in gates),
        "token_usage_totals": tracker.totals,
        "cases": rows,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
