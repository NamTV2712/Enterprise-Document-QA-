"""Attribute V6 answer-relevancy regressions without provider calls.

The audit compares the failed V6 candidate with the promoted V5 official
result while re-rendering both contexts from the frozen Phase 1 artifact. It
identifies answer drift on unchanged contexts so a provider/runtime variance
is not incorrectly treated as a fact-selector retrieval failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.run_evaluation_phase2 import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V5,
    CONTEXT_STRATEGY_SELECTIVE_V6,
    render_case_context,
)
from src.evaluation.generation_checkpoint import parse_evidence_context
from src.evaluation.test_set import TEST_SET


OFFICIAL_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
CANDIDATE_RESULTS_PATH = Path(
    "data/eval_artifacts/phase2_results_fact_evidence_v1_candidate.json"
)
DEFAULT_OUTPUT = Path("data/diagnostics/fact_candidate_variance_v1.json")
EXPECTED_OFFICIAL_SHA256 = (
    "sha256:a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba"
)
EXPECTED_CANDIDATE_SHA256 = (
    "sha256:9aebcd4661530cf89888d08d191789bc566adf3933ac2a18227a51a75dd65fe7"
)
REGRESSION_QUESTIONS = (
    "What quality and manufacturing risks does Apple mention?",
    "How does Microsoft describe its Azure and cloud services growth?",
    "What are the main sources of revenue for Microsoft?",
)
SCORE_KEYS = ("faithfulness", "answer_relevancy", "context_precision")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _text_sha256(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _answer_hash(answer: str) -> str:
    return _text_sha256(answer)


def _score(case: dict[str, Any], key: str) -> float | None:
    value = (case.get("scores") or {}).get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _context_summary(context: str) -> dict[str, Any]:
    blocks = parse_evidence_context(context)
    return {
        "context_sha256": _text_sha256(context),
        "source_count": len(blocks),
        "source_boundary_parse_passed": all(
            isinstance(block.get("text"), str) and block.get("text")
            for block in blocks
        ),
    }


def build_variance_report(
    official: dict[str, Any],
    candidate: dict[str, Any],
    artifact: dict[str, Any],
    *,
    official_path: Path = OFFICIAL_RESULTS_PATH,
    candidate_path: Path = CANDIDATE_RESULTS_PATH,
    artifact_path: Path = ARTIFACT_PATH,
) -> dict[str, Any]:
    """Build a deterministic answer-drift attribution report."""
    metadata = {case.question: case for case in TEST_SET}
    artifact_by_question = {
        case["question"]: case for case in artifact.get("cases", [])
    }
    official_by_question = {
        case["question"]: case for case in official.get("cases", [])
    }
    candidate_by_question = {
        case["question"]: case for case in candidate.get("cases", [])
    }
    questions = [
        case.question
        for case in TEST_SET
        if case.priority <= 2
        and case.question in artifact_by_question
        and case.question in official_by_question
        and case.question in candidate_by_question
    ]

    rows: list[dict[str, Any]] = []
    for question in questions:
        test_case = metadata[question]
        artifact_case = artifact_by_question[question]
        official_case = official_by_question[question]
        candidate_case = candidate_by_question[question]
        official_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V5,
        )
        candidate_context = render_case_context(
            artifact_case,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
        )
        official_context_summary = _context_summary(official_context)
        candidate_context_summary = _context_summary(candidate_context)
        score_deltas = {
            key: (
                _score(candidate_case, key) - _score(official_case, key)
                if _score(candidate_case, key) is not None
                and _score(official_case, key) is not None
                else None
            )
            for key in SCORE_KEYS
        }
        context_changed = (
            official_context_summary["context_sha256"]
            != candidate_context_summary["context_sha256"]
        )
        answer_changed = (
            _answer_hash(official_case.get("answer") or "")
            != _answer_hash(candidate_case.get("answer") or "")
        )
        if context_changed:
            classification = "context_changed"
        elif answer_changed or any(
            delta not in (None, 0.0) for delta in score_deltas.values()
        ):
            classification = "unchanged_context_answer_or_judge_drift"
        else:
            classification = "unchanged_stable"
        rows.append(
            {
                "question": question,
                "category": test_case.category,
                "context_changed": context_changed,
                "answer_changed": answer_changed,
                "classification": classification,
                "official_context": official_context_summary,
                "candidate_context": candidate_context_summary,
                "official_answer_sha256": _answer_hash(
                    official_case.get("answer") or ""
                ),
                "candidate_answer_sha256": _answer_hash(
                    candidate_case.get("answer") or ""
                ),
                "official_scores": {
                    key: _score(official_case, key) for key in SCORE_KEYS
                },
                "candidate_scores": {
                    key: _score(candidate_case, key) for key in SCORE_KEYS
                },
                "score_deltas": score_deltas,
            }
        )

    by_question = {row["question"]: row for row in rows}
    regressions = [
        row["question"]
        for row in rows
        if row["score_deltas"]["answer_relevancy"] is not None
        and row["score_deltas"]["answer_relevancy"] < 0
    ]
    changed_contexts = [row["question"] for row in rows if row["context_changed"]]
    non_fact_questions = [
        row["question"] for row in rows if row["category"] != "fact_lookup"
    ]
    regression_rows = [by_question.get(question) for question in REGRESSION_QUESTIONS]
    gates = {
        "official_hash_pinned": _file_sha256(official_path)
        == EXPECTED_OFFICIAL_SHA256,
        "candidate_hash_pinned": _file_sha256(candidate_path)
        == EXPECTED_CANDIDATE_SHA256,
        "case_set_complete": len(rows) == 30
        and {row["question"] for row in rows}
        == {case.question for case in TEST_SET if case.priority <= 2},
        "non_fact_contexts_byte_identical": all(
            not by_question[question]["context_changed"]
            for question in non_fact_questions
        ),
        "changed_contexts_are_fact_lookup": all(
            by_question[question]["category"] == "fact_lookup"
            for question in changed_contexts
        ),
        "observed_regressions_match": tuple(regressions) == tuple(
            question
            for question in REGRESSION_QUESTIONS
            if question in regressions
        )
        and set(regressions) == set(REGRESSION_QUESTIONS),
        "regressions_have_unchanged_context": all(
            row is not None and not row["context_changed"]
            for row in regression_rows
        ),
        "regressions_have_answer_drift": all(
            row is not None and row["answer_changed"] for row in regression_rows
        ),
    }
    return {
        "schema_version": 1,
        "audit": "fact_candidate_variance_v1",
        "official": False,
        "decision": (
            "provider_or_runtime_variance_on_unchanged_contexts; no retrieval "
            "correction or admission-threshold relaxation is authorized"
        ),
        "official_path": str(official_path),
        "official_sha256": _file_sha256(official_path),
        "candidate_path": str(candidate_path),
        "candidate_sha256": _file_sha256(candidate_path),
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
        "official_strategy": CONTEXT_STRATEGY_SELECTIVE_V5,
        "candidate_strategy": CONTEXT_STRATEGY_SELECTIVE_V6,
        "num_cases": len(rows),
        "changed_context_questions": changed_contexts,
        "answer_relevancy_regression_questions": regressions,
        "cases": rows,
        "gates": gates,
        "passed": all(gates.values()),
    }


def run(
    *,
    official_path: Path = OFFICIAL_RESULTS_PATH,
    candidate_path: Path = CANDIDATE_RESULTS_PATH,
    artifact_path: Path = ARTIFACT_PATH,
    output: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    """Load pinned local artifacts and write the variance report."""
    official = json.loads(official_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    artifact, _ = load_bound_artifact(
        artifact_path,
        EXPECTED_ARTIFACT_FINGERPRINT,
        CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    report = build_variance_report(
        official,
        candidate,
        artifact,
        official_path=official_path,
        candidate_path=candidate_path,
        artifact_path=artifact_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--official", type=Path, default=OFFICIAL_RESULTS_PATH)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_RESULTS_PATH)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = run(
        official_path=args.official,
        candidate_path=args.candidate,
        artifact_path=args.artifact,
        output=args.output,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
