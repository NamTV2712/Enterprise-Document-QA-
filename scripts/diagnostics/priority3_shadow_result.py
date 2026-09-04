"""Audit a complete Priority-3 Phase 2 shadow without publishing it as official.

The audit joins the frozen Phase 1 artifact with the generation and judge
checkpoints.  It refuses to report judge metrics unless every selected case
has complete generation and judging provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.evaluation.answer_contract import audit_answer
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    pack_case_context,
)
from src.evaluation.test_case_selector import select_test_cases
from src.evaluation.test_set import TEST_SET


DEFAULT_ARTIFACT = Path("data/eval_artifacts/phase1_priority3_shadow_v1.json")
DEFAULT_RESULT = Path("data/eval_artifacts/phase2_results_priority3_shadow_v1.json")
DEFAULT_GENERATION = Path(
    "data/eval_artifacts/phase2_gen_priority3_shadow_v1.jsonl"
)
DEFAULT_JUDGE = Path(
    "data/eval_artifacts/phase2_judge_priority3_shadow_v1.jsonl"
)
DEFAULT_OFFICIAL = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/priority3_shadow_v1_complete.json")
OFFICIAL_N30_SHA256 = (
    "a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _citation_numbers(answer: str) -> tuple[int, ...]:
    return tuple(
        int(value)
        for value in re.findall(r"[\[【]Source\s+(\d+)[\]】]", answer, re.I)
    )


def _assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise SystemExit(f"{label}: expected {expected!r}, got {actual!r}")


def build_report(
    artifact_path: Path,
    result_path: Path,
    generation_path: Path,
    judge_path: Path,
    official_path: Path,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    generation = _read_jsonl(generation_path)
    judging = _read_jsonl(judge_path)
    selected = select_test_cases(TEST_SET, priority=3, exact_priority=True)
    selected_questions = [case.question for case in selected.cases]
    artifact_questions = [case["question"] for case in artifact.get("cases", [])]
    generation_by_question = {row.get("question"): row for row in generation}
    judge_by_question = {row.get("question"): row for row in judging}

    expected_selection = selected.provenance()
    actual_selection = artifact.get("selection")
    selection_keys = (
        "selector",
        "selection_scope",
        "priority",
        "exact_priority",
        "selected_case_count",
        "selected_questions_sha256",
    )
    selection_ok = all(
        isinstance(actual_selection, dict)
        and actual_selection.get(key) == expected_selection.get(key)
        for key in selection_keys
    )

    generation_ok = all(
        generation_by_question.get(question, {}).get("status") == "OK"
        for question in selected_questions
    )
    judging_ok = all(
        judge_by_question.get(question, {}).get("status") == "OK"
        for question in selected_questions
    )
    unique_generation = len(generation) == len(generation_by_question)
    unique_judging = len(judging) == len(judge_by_question)
    binding_values = sorted(
        {row.get("binding") for row in generation if row.get("binding")}
    )
    result_binding = result.get("binding")
    one_binding = len(binding_values) == 1 and result_binding == binding_values[0]
    official_sha = _sha256(official_path).removeprefix("sha256:")

    integrity_rows: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    category_scores: dict[str, dict[str, list[float]]] = {}
    artifact_by_question = {
        case["question"]: case for case in artifact.get("cases", [])
    }
    for question in selected_questions:
        case = artifact_by_question[question]
        generated = generation_by_question.get(question, {})
        judge = judge_by_question.get(question, {})
        answer = generated.get("answer", "")
        packed = pack_case_context(
            case,
            required_keywords=case.get("required_keywords"),
            strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
        )
        integrity = audit_answer(answer, [entry.get("text", "") for entry in packed.kept])
        missing_keywords = [
            keyword
            for keyword in case.get("required_keywords", [])
            if str(keyword).casefold() not in answer.casefold()
        ]
        scores = judge.get("scores") or {}
        category = case.get("category", "unknown")
        category_counts[category] += 1
        category_scores.setdefault(
            category,
            {name: [] for name in ("faithfulness", "answer_relevancy", "context_precision")},
        )
        for name in category_scores[category]:
            value = scores.get(name)
            if isinstance(value, (int, float)):
                category_scores[category][name].append(float(value))
        integrity_rows.append(
            {
                "question": question,
                "category": category,
                "context_source_count": len(packed.kept),
                "citations": _citation_numbers(answer),
                "citation_correct": not integrity.out_of_range_citations
                and not integrity.uncited_answer,
                "fallback": integrity.fallback_answer,
                "unsupported_numeric_claims": list(
                    integrity.unsupported_numeric_claims
                ),
                "missing_required_keywords": missing_keywords,
                "generation_status": generated.get("status"),
                "judge_status": judge.get("status"),
            }
        )

    category_metrics = {
        category: {
            name: round(sum(values) / len(values), 4) if values else None
            for name, values in metrics.items()
        }
        | {"num_cases": category_counts[category]}
        for category, metrics in sorted(category_scores.items())
    }
    deterministic_ok = all(
        row["citation_correct"]
        and not row["fallback"]
        and not row["unsupported_numeric_claims"]
        and not row["missing_required_keywords"]
        for row in integrity_rows
    )
    complete = (
        len(artifact_questions) == 22
        and artifact_questions == selected_questions
        and len(generation) == 22
        and len(judging) == 22
        and generation_ok
        and judging_ok
        and unique_generation
        and unique_judging
        and selection_ok
        and one_binding
        and result.get("official") is False
        and result.get("provider_complete") is True
    )
    return {
        "schema_version": 1,
        "audit": "priority3_shadow_v1_complete",
        "official": False,
        "promotion_eligible": False,
        "artifact_path": str(artifact_path),
        "result_path": str(result_path),
        "generation_checkpoint": str(generation_path),
        "judge_checkpoint": str(judge_path),
        "artifact_file_sha256": _sha256(artifact_path),
        "result_file_sha256": _sha256(result_path),
        "official_n30_sha256": official_sha,
        "official_n30_unchanged": official_sha == OFFICIAL_N30_SHA256,
        "context_strategy": result.get("context_strategy"),
        "binding": result_binding,
        "selection": actual_selection,
        "counts": {
            "selected": len(selected_questions),
            "artifact": len(artifact_questions),
            "generation": len(generation),
            "generation_ok": sum(
                row.get("status") == "OK" for row in generation
            ),
            "judging": len(judging),
            "judging_ok": sum(row.get("status") == "OK" for row in judging),
        },
        "category_metrics": category_metrics if complete else {},
        "deterministic": {
            "passed": deterministic_ok,
            "rows": integrity_rows,
        },
        "gates": {
            "exact_p3_scope": len(artifact_questions) == 22
            and artifact_questions == selected_questions,
            "complete_generation": generation_ok
            and len(generation) == 22
            and unique_generation,
            "complete_judging": judging_ok and len(judging) == 22 and unique_judging,
            "selection_provenance": selection_ok,
            "one_generation_binding": one_binding,
            "provider_complete": result.get("provider_complete") is True,
            "official_false": result.get("official") is False,
            "deterministic_integrity": deterministic_ok,
            "official_n30_unchanged": official_sha == OFFICIAL_N30_SHA256,
        },
        "passed": complete and deterministic_ok and official_sha == OFFICIAL_N30_SHA256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--generation", type=Path, default=DEFAULT_GENERATION)
    parser.add_argument("--judge", type=Path, default=DEFAULT_JUDGE)
    parser.add_argument("--official", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(
        args.artifact,
        args.result,
        args.generation,
        args.judge,
        args.official,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
