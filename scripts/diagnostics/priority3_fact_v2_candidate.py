"""Audit the complete non-official P3 Fact Evidence Sufficiency v2 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.diagnostics.priority3_fact_evidence_sufficiency_v2 import (
    run as run_context_audit,
)
from src.evaluation.test_case_selector import select_test_cases
from src.evaluation.test_set import TEST_SET


DEFAULT_ARTIFACT = Path("data/eval_artifacts/phase1_priority3_shadow_v1.json")
DEFAULT_BASELINE_RESULT = Path(
    "data/eval_artifacts/phase2_results_priority3_shadow_v1.json"
)
DEFAULT_BASELINE_GENERATION = Path(
    "data/eval_artifacts/phase2_gen_priority3_shadow_v1.jsonl"
)
DEFAULT_BASELINE_JUDGE = Path(
    "data/eval_artifacts/phase2_judge_priority3_shadow_v1.jsonl"
)
DEFAULT_RESULT = Path(
    "data/eval_artifacts/phase2_results_priority3_fact_v2_candidate.json"
)
DEFAULT_GENERATION = Path(
    "data/eval_artifacts/phase2_gen_priority3_fact_v2_candidate.jsonl"
)
DEFAULT_JUDGE = Path(
    "data/eval_artifacts/phase2_judge_priority3_fact_v2_candidate.jsonl"
)
DEFAULT_OFFICIAL = Path("data/eval_artifacts/phase2_results_packed_selective_v2.json")
DEFAULT_REPRODUCIBILITY = Path(
    "data/diagnostics/priority3_fact_v2_reproducibility.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/priority3_fact_v2_candidate.json")
OFFICIAL_N30_SHA256 = (
    "a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
EXPECTED_CASE_COUNT = 22
EXPECTED_FACT_COUNT = 9
MIN_AR_DRIFT = -0.0050


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _rows_by_question(path: Path) -> dict[str, dict[str, Any]]:
    rows = _read_jsonl(path)
    return {row["question"]: row for row in rows}


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _judge_metrics(
    rows: dict[str, dict[str, Any]],
    questions: list[str],
    categories_by_question: dict[str, str],
) -> dict[str, Any]:
    metric_names = ("faithfulness", "answer_relevancy", "context_precision")
    values = {
        name: [
            float((rows[question].get("scores") or {})[name])
            for question in questions
            if isinstance((rows.get(question, {}).get("scores") or {}).get(name), (int, float))
        ]
        for name in metric_names
    }
    categories: dict[str, dict[str, list[float]]] = {}
    for question in questions:
        category = categories_by_question.get(question, "unknown")
        scores = rows[question].get("scores") or {}
        bucket = categories.setdefault(category, {name: [] for name in metric_names})
        for name in metric_names:
            if isinstance(scores.get(name), (int, float)):
                bucket[name].append(float(scores[name]))
    return {
        name: _average(items) for name, items in values.items()
    } | {
        "overall_judge_average": _average(
            [score for name in metric_names for score in values[name]]
        ),
        "categories": {
            category: {
                "num_cases": len(next(iter(metrics.values()), [])),
                **{name: _average(items) for name, items in metrics.items()},
            }
            for category, metrics in sorted(categories.items())
        },
    }


def _result_metric(result: dict[str, Any], name: str) -> float | None:
    value = (result.get("metrics") or {}).get(name)
    return float(value) if isinstance(value, (int, float)) else None


def _metric_matches_result(
    computed: dict[str, Any], result: dict[str, Any]
) -> bool:
    for name in ("faithfulness", "answer_relevancy", "context_precision", "overall_judge_average"):
        if computed.get(name) != _result_metric(result, name):
            return False
    return all(
        computed["categories"].get(category) == metrics
        for category, metrics in ((result.get("metrics") or {}).get("categories") or {}).items()
    )


def build_report(
    artifact_path: Path = DEFAULT_ARTIFACT,
    baseline_result_path: Path = DEFAULT_BASELINE_RESULT,
    baseline_generation_path: Path = DEFAULT_BASELINE_GENERATION,
    baseline_judge_path: Path = DEFAULT_BASELINE_JUDGE,
    result_path: Path = DEFAULT_RESULT,
    generation_path: Path = DEFAULT_GENERATION,
    judge_path: Path = DEFAULT_JUDGE,
    official_path: Path = DEFAULT_OFFICIAL,
    reproducibility_path: Path = DEFAULT_REPRODUCIBILITY,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    baseline_result = json.loads(baseline_result_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    selected = select_test_cases(TEST_SET, priority=3, exact_priority=True)
    questions = [case.question for case in selected.cases]
    artifact_questions = [case["question"] for case in artifact.get("cases", [])]

    baseline_generation_rows = _read_jsonl(baseline_generation_path)
    baseline_judge_rows = _read_jsonl(baseline_judge_path)
    generation_rows = _read_jsonl(generation_path)
    judge_rows = _read_jsonl(judge_path)
    baseline_generation = {row["question"]: row for row in baseline_generation_rows}
    baseline_judge = {row["question"]: row for row in baseline_judge_rows}
    generation = {row["question"]: row for row in generation_rows}
    judging = {row["question"]: row for row in judge_rows}
    categories_by_question = {
        case["question"]: case.get("category", "unknown")
        for case in artifact.get("cases", [])
    }

    baseline_metrics = _judge_metrics(baseline_judge, questions, categories_by_question)
    candidate_metrics = _judge_metrics(judging, questions, categories_by_question)
    context_audit = run_context_audit(
        artifact_path=artifact_path,
        generation_path=generation_path,
        official_path=official_path,
        output=None,
    )

    generation_bindings = sorted(
        {row.get("binding") for row in generation_rows if row.get("binding")}
    )
    result_binding = result.get("binding")
    one_generation_binding = (
        len(generation_bindings) == 1 and result_binding == generation_bindings[0]
    )
    generation_complete = (
        len(generation_rows) == EXPECTED_CASE_COUNT
        and len(generation) == EXPECTED_CASE_COUNT
        and set(generation) == set(questions)
        and all(generation[question].get("status") == "OK" for question in questions)
    )
    judging_complete = (
        len(judge_rows) == EXPECTED_CASE_COUNT
        and len(judging) == EXPECTED_CASE_COUNT
        and set(judging) == set(questions)
        and all(judging[question].get("status") == "OK" for question in questions)
    )
    baseline_complete = (
        len(baseline_generation_rows) == EXPECTED_CASE_COUNT
        and len(baseline_judge_rows) == EXPECTED_CASE_COUNT
        and len(baseline_generation) == EXPECTED_CASE_COUNT
        and len(baseline_judge) == EXPECTED_CASE_COUNT
        and all(baseline_generation[question].get("status") == "OK" for question in questions)
        and all(baseline_judge[question].get("status") == "OK" for question in questions)
    )
    per_case_faithfulness_non_regression = all(
        float((judging[question].get("scores") or {}).get("faithfulness", -1))
        >= float((baseline_judge[question].get("scores") or {}).get("faithfulness", -1))
        for question in questions
    ) if generation_complete and judging_complete and baseline_complete else False
    per_case_deltas = {
        question: {
            name: round(
                float((judging[question].get("scores") or {})[name])
                - float((baseline_judge[question].get("scores") or {})[name]),
                4,
            )
            for name in ("faithfulness", "answer_relevancy", "context_precision")
        }
        for question in questions
        if question in judging and question in baseline_judge
    }
    official_sha = _sha256(official_path).removeprefix("sha256:")
    repro = json.loads(reproducibility_path.read_text(encoding="utf-8"))

    gates = {
        "exact_p3_scope": len(artifact_questions) == EXPECTED_CASE_COUNT
        and artifact_questions == questions,
        "complete_generation": generation_complete,
        "complete_judging": judging_complete,
        "baseline_complete": baseline_complete,
        "one_generation_binding": one_generation_binding,
        "candidate_strategy": result.get("context_strategy")
        == "selective_packed_v7_fact_generalization_candidate",
        "provider_complete": result.get("provider_complete") is True
        and result.get("stopped_reason") is None,
        "official_false": result.get("official") is False,
        "metrics_match_result": _metric_matches_result(candidate_metrics, result),
        "faithfulness_non_regression": candidate_metrics["faithfulness"]
        >= baseline_metrics["faithfulness"]
        and per_case_faithfulness_non_regression,
        "answer_relevancy_bounded": candidate_metrics["answer_relevancy"]
        >= baseline_metrics["answer_relevancy"] + MIN_AR_DRIFT,
        "context_precision_non_regression": candidate_metrics["context_precision"]
        >= baseline_metrics["context_precision"],
        "fact_context_gain": (
            (candidate_metrics["categories"].get("fact_lookup") or {}).get(
                "context_precision"
            )
            >= (baseline_metrics["categories"].get("fact_lookup") or {}).get(
                "context_precision", 0
            )
            + 0.15
        ),
        "fact_case_count": sum(
            case.get("category") == "fact_lookup" for case in artifact.get("cases", [])
        )
        == EXPECTED_FACT_COUNT,
        "context_structural_gates": context_audit.get("passed") is True,
        "reproducibility_gate": repro.get("passed") is True
        and repro.get("candidate_strategy")
        == "selective_packed_v7_fact_generalization_candidate",
        "official_n30_unchanged": official_sha == OFFICIAL_N30_SHA256,
    }
    return {
        "schema_version": 1,
        "audit": "priority3_fact_v2_candidate",
        "official": False,
        "promotion_eligible": False,
        "artifact_path": str(artifact_path),
        "baseline_result_path": str(baseline_result_path),
        "result_path": str(result_path),
        "generation_checkpoint": str(generation_path),
        "judge_checkpoint": str(judge_path),
        "result_file_sha256": _sha256(result_path),
        "generation_file_sha256": _sha256(generation_path),
        "judge_file_sha256": _sha256(judge_path),
        "official_n30_sha256": official_sha,
        "context_strategy": result.get("context_strategy"),
        "binding": result_binding,
        "selected": len(questions),
        "counts": {
            "generation": len(generation_rows),
            "generation_ok": sum(row.get("status") == "OK" for row in generation.values()),
            "judging": len(judge_rows),
            "judging_ok": sum(row.get("status") == "OK" for row in judging.values()),
        },
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "metric_deltas": {
            name: round(candidate_metrics[name] - baseline_metrics[name], 4)
            for name in (
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "overall_judge_average",
            )
        },
        "per_case_deltas": per_case_deltas,
        "context_audit": {
            "audit": context_audit.get("audit"),
            "passed": context_audit.get("passed"),
            "fact_baseline_text_chars": context_audit.get("fact_baseline_text_chars"),
            "fact_candidate_text_chars": context_audit.get("fact_candidate_text_chars"),
            "fact_text_reduction_ratio": context_audit.get("fact_text_reduction_ratio"),
            "gates": context_audit.get("gates"),
        },
        "reproducibility": {
            "path": str(reproducibility_path),
            "sha256": _sha256(reproducibility_path),
            "audit": repro.get("audit"),
            "passed": repro.get("passed"),
        },
        "gates": gates,
        "passed": all(gates.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--baseline-result", type=Path, default=DEFAULT_BASELINE_RESULT)
    parser.add_argument("--baseline-generation", type=Path, default=DEFAULT_BASELINE_GENERATION)
    parser.add_argument("--baseline-judge", type=Path, default=DEFAULT_BASELINE_JUDGE)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--generation", type=Path, default=DEFAULT_GENERATION)
    parser.add_argument("--judge", type=Path, default=DEFAULT_JUDGE)
    parser.add_argument("--official", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("--reproducibility", type=Path, default=DEFAULT_REPRODUCIBILITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_report(
        artifact_path=args.artifact,
        baseline_result_path=args.baseline_result,
        baseline_generation_path=args.baseline_generation,
        baseline_judge_path=args.baseline_judge,
        result_path=args.result,
        generation_path=args.generation,
        judge_path=args.judge,
        official_path=args.official,
        reproducibility_path=args.reproducibility,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
