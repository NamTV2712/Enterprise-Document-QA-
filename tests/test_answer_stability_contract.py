import json
from pathlib import Path

from scripts.diagnostics.answer_stability_contract import build_report

from tests.conftest import skip_without_data


@skip_without_data(
    "data/eval_artifacts/phase1_priority2.json",
    "data/eval_artifacts/phase2_results_packed_selective_v2.json",
)
def test_answer_stability_contract_is_provider_free_and_detects_known_omission() -> None:
    root = Path("data/eval_artifacts")
    artifact = json.loads(
        (root / "phase1_priority2.json").read_text(encoding="utf-8")
    )
    official = json.loads(
        (root / "phase2_results_packed_selective_v2.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = json.loads(
        (root / "phase2_results_fact_evidence_v1_candidate.json").read_text(
            encoding="utf-8"
        )
    )

    report = build_report(artifact, official, candidate)

    assert report["gates"]["artifact_fingerprint_pinned"] is True
    assert report["gates"]["official_stability_passes"] is True
    assert report["gates"]["known_candidate_azure_omission_is_detected"] is True
    assert report["passed"] is True
