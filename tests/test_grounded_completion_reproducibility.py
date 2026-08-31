from scripts.diagnostics.grounded_completion_reproducibility import build_report


QUESTIONS = {"aws", "cyber", "azure"}


def _report(replicate_id: str) -> dict:
    return {
        "audit": "grounded_completion_v3_sentinel",
        "replicate_id": replicate_id,
        "provider_complete": True,
        "passed": True,
        "context_strategy": "selective_packed_v4_candidate",
        "bound_artifact_fingerprint": "sha256:artifact",
        "binding": "sha256:binding",
        "completion_fingerprint": "sha256:completion",
        "sentinel_questions": sorted(QUESTIONS),
        "gates": {
            "provider_complete": True,
            "deterministic_passed": True,
            "score_regression_passed": True,
        },
        "replicate_provenance": {
            "generation_answer_hashes": {
                question: "sha256:answer" for question in QUESTIONS
            },
            "generation_bindings": {
                question: "sha256:binding" for question in QUESTIONS
            },
            "judge_bindings": {
                question: "sha256:judge" for question in QUESTIONS
            },
        },
    }


def test_reproducibility_requires_two_complete_replicates() -> None:
    result = build_report([_report("r1"), _report("r2")])

    assert result["passed"] is True
    assert result["replicate_pass_count"] == 2
    assert result["replicate_pass_rate"] == 1.0
    assert result["gates"]["one_completion_fingerprint"] is True
