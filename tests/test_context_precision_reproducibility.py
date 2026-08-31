from __future__ import annotations

from scripts.diagnostics.context_precision_reproducibility import build_report
from scripts.run_context_precision_sentinel import SENTINEL_QUESTIONS


def _replicate(replicate_id: str, passed: bool = True) -> dict:
    answers = {
        question: f"sha256:{index + 1:064d}"
        for index, question in enumerate(SENTINEL_QUESTIONS)
    }
    bindings = {
        question: "sha256:" + "a" * 64
        for question in SENTINEL_QUESTIONS
    }
    judges = {
        question: "sha256:" + ("b" if passed else "c") * 64
        for question in SENTINEL_QUESTIONS
    }
    return {
        "replicate_id": replicate_id,
        "context_strategy": "selective_packed_v4_candidate",
        "bound_artifact_fingerprint": "sha256:" + "d" * 64,
        "binding": "sha256:" + "e" * 64,
        "provider_complete": True,
        "gates": {
            "provider_complete": True,
            "deterministic_passed": True,
            "score_regression_passed": passed,
        },
        "candidate_aggregate": {
            "faithfulness": 1.0 if passed else 0.9,
            "answer_relevancy": 1.0,
            "context_precision": 0.8,
        },
        "replicate_provenance": {
            "replicate_id": replicate_id,
            "generation_answer_hashes": answers,
            "generation_bindings": bindings,
            "judge_bindings": judges,
        },
    }


def test_reproducibility_requires_two_complete_replicates() -> None:
    report = build_report([_replicate("r1"), _replicate("r2")])

    assert report["passed"] is True
    assert report["replicate_pass_count"] == 2
    assert report["replicate_pass_rate"] == 1.0
    assert report["pre_registered_rule"]["best_of_selection_forbidden"] is True


def test_reproducibility_rejects_one_failed_replicate() -> None:
    report = build_report([_replicate("r1"), _replicate("r2", passed=False)])

    assert report["passed"] is False
    assert report["gates"]["all_replicates_pass"] is False
    assert report["replicate_pass_count"] == 1


def test_reproducibility_rejects_duplicate_ids_and_missing_provenance() -> None:
    duplicate = _replicate("r1")
    missing = _replicate("r1")
    missing["replicate_provenance"]["judge_bindings"] = {}
    report = build_report([duplicate, missing])

    assert report["passed"] is False
    assert report["gates"]["unique_replicate_ids"] is False
    assert report["gates"]["complete_provenance"] is False
