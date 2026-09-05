"""Measure judge variance on frozen answers with a hard call budget."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from scripts.run_answerability_stability_sentinel import (
    SENTINEL_QUESTIONS,
    ProviderCallBudget,
)
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V7, render_case_context
from src.evaluation.phase2_runtime import (
    UsageTracker,
    build_production_judge_prompt,
    judging_pool_keys,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.generation.comparative_answerability import COMPARATIVE_ANSWERABILITY_FINGERPRINT
from src.generation.comparative_answer_renderer import COMPARATIVE_ANSWER_RENDERER_FINGERPRINT
from src.generation.generator import Generator


DEFAULT_R1 = Path("data/eval_artifacts/answerability_stability_v4_sentinel_summary_r1.json")
DEFAULT_R2 = Path("data/eval_artifacts/answerability_stability_v4_sentinel_summary_r2.json")
DEFAULT_ARTIFACT = Path("data/eval_artifacts/phase1_priority2_financial_table_units.json")
DEFAULT_OUTPUT = Path("data/diagnostics/comparative_judge_variance_v2.json")
MAX_CALLS = 24


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _answers(report: dict[str, Any]) -> dict[str, str]:
    rows = {
        row.get("question"): row.get("answer")
        for row in report.get("cases", [])
        if isinstance(row, dict)
    }
    missing = [question for question in SENTINEL_QUESTIONS if not isinstance(rows.get(question), str)]
    if missing:
        raise ValueError(f"report is missing frozen answers: {missing}")
    return {question: rows[question] for question in SENTINEL_QUESTIONS}


def _score(record: dict[str, Any]) -> dict[str, float] | None:
    scores = record.get("scores")
    if not isinstance(scores, dict):
        return None
    keys = ("faithfulness", "answer_relevancy", "context_precision")
    if not all(isinstance(scores.get(key), (int, float)) for key in keys):
        return None
    return {key: float(scores[key]) for key in keys}


def run(
    *,
    r1: Path = DEFAULT_R1,
    r2: Path = DEFAULT_R2,
    artifact_path: Path = DEFAULT_ARTIFACT,
    output: Path = DEFAULT_OUTPUT,
    max_calls: int = MAX_CALLS,
) -> dict[str, Any]:
    if max_calls < 1 or max_calls > MAX_CALLS:
        raise ValueError(f"max_calls must be between 1 and {MAX_CALLS}")
    report_one = _load(r1)
    report_two = _load(r2)
    answers_by_replicate = {"r1": _answers(report_one), "r2": _answers(report_two)}
    artifact = _load(artifact_path)
    artifact_by_question = {case["question"]: case for case in artifact["cases"]}
    test_by_question = {case.question: case for case in TEST_SET}
    contexts: dict[str, str] = {}
    for question in SENTINEL_QUESTIONS:
        test_case = test_by_question[question]
        contexts[question] = render_case_context(
            artifact_by_question[question],
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )

    tracker = UsageTracker()
    budget = ProviderCallBudget(max_calls)
    judge = budget.wrap(make_judge_call(Generator(model=report_one.get("model") or "openai/gpt-oss-120b", api_keys=judging_pool_keys()), tracker))
    rows: list[dict[str, Any]] = []
    for replicate_id, answers in answers_by_replicate.items():
        for question in SENTINEL_QUESTIONS:
            answer = answers[question]
            prompt = build_production_judge_prompt(
                question,
                answer,
                contexts[question],
                test_by_question[question].ground_truth,
            )
            for repeat_index in (1, 2):
                row: dict[str, Any] = {
                    "replicate_id": replicate_id,
                    "repeat_index": repeat_index,
                    "question": question,
                    "answer_sha256": _sha256_text(answer),
                    "context_sha256": _sha256_text(contexts[question]),
                    "prompt_sha256": _sha256_text(prompt),
                }
                try:
                    scores = judge(prompt)
                except Exception as error:  # provider failures are recorded data
                    row.update({"status": "ERROR", "error": str(error)[:300]})
                else:
                    row.update({"status": "OK", "scores": scores})
                rows.append(row)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["replicate_id"], row["question"]), []).append(row)
    variability: list[dict[str, Any]] = []
    for key, group in grouped.items():
        scores = [_score(row) for row in group]
        complete = all(score is not None for score in scores)
        ranges = {
            metric: (
                max(score[metric] for score in scores if score is not None)
                - min(score[metric] for score in scores if score is not None)
                if complete
                else None
            )
            for metric in ("faithfulness", "answer_relevancy", "context_precision")
        }
        variability.append({
            "replicate_id": key[0],
            "question": key[1],
            "same_answer": len({row["answer_sha256"] for row in group}) == 1,
            "complete": complete,
            "score_ranges": ranges,
            "score_changed_on_same_answer": complete and any(value > 0 for value in ranges.values()),
        })

    provider_complete = len(rows) == 2 * len(SENTINEL_QUESTIONS) * 2 and all(
        row.get("status") == "OK" for row in rows
    )
    report = {
        "schema_version": 2,
        "audit": "comparative_judge_variance_v2",
        "official": False,
        "provider_complete": provider_complete,
        "max_provider_calls": max_calls,
        "provider_calls_used": budget.used,
        "within_budget": budget.used <= max_calls,
        "inputs": {
            "r1": {"path": str(r1), "sha256": _sha256_text(r1.read_text(encoding="utf-8"))},
            "r2": {"path": str(r2), "sha256": _sha256_text(r2.read_text(encoding="utf-8"))},
            "artifact": {"path": str(artifact_path), "sha256": _sha256_text(artifact_path.read_text(encoding="utf-8"))},
        },
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_FINGERPRINT,
        "comparative_answer_renderer_fingerprint": COMPARATIVE_ANSWER_RENDERER_FINGERPRINT,
        "repeat_design": {
            "answers": 12,
            "judge_repeats_per_answer": 2,
            "judge_calls": 24,
            "answer_and_context_frozen": True,
            "selection_or_averaging_forbidden": True,
        },
        "rows": rows,
        "variability": variability,
        "gates": {
            "provider_complete": provider_complete,
            "same_answer_inputs": all(item["same_answer"] for item in variability),
            "all_repeat_groups_complete": all(item["complete"] for item in variability),
            "within_budget": budget.used <= max_calls,
        },
    }
    report["passed"] = all(report["gates"].values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--r2", type=Path, default=DEFAULT_R2)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-calls", type=int, default=MAX_CALLS)
    args = parser.parse_args(argv)
    report = run(
        r1=args.r1,
        r2=args.r2,
        artifact_path=args.artifact,
        output=args.output,
        max_calls=args.max_calls,
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
