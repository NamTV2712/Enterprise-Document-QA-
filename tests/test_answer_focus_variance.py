from scripts.diagnostics.answer_focus_variance import build_report

from tests.conftest import skip_without_data


@skip_without_data(
    "data/eval_artifacts/phase1_priority2.json",
    "data/eval_artifacts/phase2_results_packed_selective_v2.json",
    "data/eval_artifacts/phase2_results_answer_stability_v7_candidate.json",
    "data/eval_artifacts/answer_stability_v1_sentinel_summary_r1.json",
    "data/eval_artifacts/answer_stability_v1_sentinel_summary_r2.json",
)
def test_real_answer_focus_variance_pins_two_expected_regressions(tmp_path) -> None:
    import json
    from pathlib import Path

    root = Path("data")
    official_path = root / "eval_artifacts/phase2_results_packed_selective_v2.json"
    candidate_path = root / "eval_artifacts/phase2_results_answer_stability_v7_candidate.json"
    sentinel_r1_path = root / "eval_artifacts/answer_stability_v1_sentinel_summary_r1.json"
    sentinel_r2_path = root / "eval_artifacts/answer_stability_v1_sentinel_summary_r2.json"
    artifact_path = root / "eval_artifacts/phase1_priority2.json"

    report = build_report(
        json.loads(official_path.read_text(encoding="utf-8")),
        json.loads(candidate_path.read_text(encoding="utf-8")),
        json.loads(sentinel_r1_path.read_text(encoding="utf-8")),
        json.loads(sentinel_r2_path.read_text(encoding="utf-8")),
        json.loads(artifact_path.read_text(encoding="utf-8")),
        official_path=official_path,
        candidate_path=candidate_path,
        sentinel_r1_path=sentinel_r1_path,
        sentinel_r2_path=sentinel_r2_path,
        artifact_path=artifact_path,
    )

    assert report["passed"] is True
    assert report["num_cases"] == 30
    assert report["gates"]["microsoft_risk_overdetail_observed"] is True
    assert report["gates"]["apple_judge_variance_observed"] is True
