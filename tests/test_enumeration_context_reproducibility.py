from scripts.diagnostics.enumeration_context_reproducibility import build_report


def _report(replicate_id: str, *, passed: bool = True) -> dict:
    questions = ["q1", "q2", "q3", "q4"]
    provenance = {
        "generation_answer_hashes": {
            question: f"sha256:{question}" for question in questions
        },
        "generation_bindings": {question: "binding" for question in questions},
        "judge_bindings": {question: "binding" for question in questions},
    }
    return {
        "audit": "enumeration_context_sentinel_v1",
        "provider_complete": True,
        "passed": passed,
        "replicate_id": replicate_id,
        "context_strategy": "selective_packed_v5_enumeration_candidate",
        "bound_artifact_fingerprint": "artifact",
        "binding": "binding",
        "completion_fingerprint": "completion",
        "sentinel_questions": questions,
        "replicate_provenance": provenance,
        "gates": {"all": passed},
    }


def test_two_complete_replicates_pass() -> None:
    report = build_report([_report("r1"), _report("r2")])

    assert report["passed"]
    assert report["replicate_pass_rate"] == 1.0


def test_failed_replicate_is_not_averaged_away() -> None:
    report = build_report([_report("r1"), _report("r2", passed=False)])

    assert not report["passed"]
    assert not report["gates"]["all_replicates_pass"]
